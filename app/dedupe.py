"""
Deduplication module for preventing duplicate uploads.

This module implements two-level deduplication:
1. Primary: Instagram post ID (never re-upload same post)
2. Secondary: Perceptual hash (pHash) comparison for similar content
"""

import logging
from typing import List, Optional, Tuple, Set

import imagehash
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db_session
from .models import Download, StatusEnum, Transform

logger = logging.getLogger(__name__)


class Deduplicator:
    """Deduplication engine for preventing duplicate uploads."""
    
    def __init__(self):
        self.settings = get_settings()
        self.phash_threshold = self.settings.phash_threshold
    
    def check_duplicate_download(self, ig_post_id: str) -> bool:
        """Check if an Instagram post has already been downloaded.
        
        Args:
            ig_post_id: Instagram post ID/shortcode
            
        Returns:
            True if duplicate, False if new
        """
        with get_db_session() as session:
            existing = session.query(Download).filter_by(ig_post_id=ig_post_id).first()
            return existing is not None
    
    def check_duplicate_transform(self, transform: Transform) -> Tuple[bool, Optional[str]]:
        """Check if a transform is a duplicate based on pHash.
        
        Args:
            transform: Transform record to check
            
        Returns:
            Tuple of (is_duplicate, reason)
        """
        if not transform.phash:
            logger.warning(f"Transform {transform.id} has no pHash")
            return False, None
        
        with get_db_session() as session:
            # Get all completed transforms with pHash
            existing_transforms = session.query(Transform).filter(
                Transform.id != transform.id,  # type: ignore
                Transform.phash.isnot(None),
                Transform.status == StatusEnum.COMPLETED
            ).all()
            
            for existing_transform in existing_transforms:
                if self._compare_phashes(str(transform.phash), str(existing_transform.phash)):
                    reason = f"Similar to transform {existing_transform.id} (pHash distance: {self._phash_distance(str(transform.phash), str(existing_transform.phash))})"
                    logger.info(f"Duplicate detected: {reason}")
                    return True, reason
        
        return False, None
    
    def _compare_phashes(self, phash1: str, phash2: str) -> bool:
        """Compare two perceptual hashes for similarity.
        
        Args:
            phash1: First perceptual hash
            phash2: Second perceptual hash
            
        Returns:
            True if hashes are similar (within threshold)
        """
        try:
            # Convert string hashes back to imagehash objects
            hash1 = imagehash.hex_to_hash(phash1)
            hash2 = imagehash.hex_to_hash(phash2)
            
            # Calculate Hamming distance
            distance = hash1 - hash2
            
            # Consider similar if distance is below threshold
            return distance <= self.phash_threshold
            
        except Exception as e:
            logger.error(f"Error comparing pHashes: {e}")
            return False
    
    def _phash_distance(self, phash1: str, phash2: str) -> int:
        """Calculate Hamming distance between two pHashes.
        
        Args:
            phash1: First perceptual hash
            phash2: Second perceptual hash
            
        Returns:
            Hamming distance (0 = identical, higher = more different)
        """
        try:
            hash1 = imagehash.hex_to_hash(phash1)
            hash2 = imagehash.hex_to_hash(phash2)
            return hash1 - hash2
        except Exception as e:
            logger.error(f"Error calculating pHash distance: {e}")
            return 999  # Return high distance on error
    
    def mark_duplicate_transform(self, transform: Transform, reason: str) -> None:
        """Mark a transform as duplicate.
        
        Args:
            transform: Transform record to mark
            reason: Reason for marking as duplicate
        """
        with get_db_session() as session:
            db_transform = session.query(Transform).filter_by(id=transform.id).first()
            if db_transform:
                db_transform.status = StatusEnum.DUPLICATE
                db_transform.error_message = reason  # type: ignore
                session.commit()
                logger.info(f"Marked transform {transform.id} as duplicate: {reason}")
    
    def get_duplicate_stats(self) -> dict:
        """Get deduplication statistics."""
        with get_db_session() as session:
            total_downloads = session.query(Download).count()
            total_transforms = session.query(Transform).count()
            duplicate_transforms = session.query(Transform).filter_by(
                status=StatusEnum.DUPLICATE
            ).count()
            
            # Calculate average pHash distance for similar content
            completed_transforms = session.query(Transform).filter(
                Transform.status == StatusEnum.COMPLETED,  # type: ignore
                Transform.phash.isnot(None)
            ).all()
            
            similar_pairs = 0
            total_distance = 0
            
            for i, transform1 in enumerate(completed_transforms):
                for transform2 in completed_transforms[i+1:]:
                    distance = self._phash_distance(transform1.phash, transform2.phash)
                    if distance <= self.phash_threshold:
                        similar_pairs += 1
                        total_distance += distance
            
            avg_distance = total_distance / similar_pairs if similar_pairs > 0 else 0
            
            return {
                "total_downloads": total_downloads,
                "total_transforms": total_transforms,
                "duplicate_transforms": duplicate_transforms,
                "phash_threshold": self.phash_threshold,
                "similar_pairs_found": similar_pairs,
                "average_similarity_distance": avg_distance,
            }
    
    def process_transforms_for_duplicates(self) -> List[Transform]:
        """Process all transforms to check for duplicates.
        
        Returns:
            List of transforms marked as duplicates
        """
        duplicates = []
        
        with get_db_session() as session:
            # Get all completed transforms that haven't been checked for duplicates
            transforms = session.query(Transform).filter(
                Transform.status == StatusEnum.COMPLETED,  # type: ignore
                Transform.phash.isnot(None)
            ).all()
            
            for transform in transforms:
                is_duplicate, reason = self.check_duplicate_transform(transform)
                if is_duplicate:
                    self.mark_duplicate_transform(transform, reason or "Duplicate found")
                    duplicates.append(transform)
        
        logger.info(f"Found {len(duplicates)} duplicate transforms")
        return duplicates
    
    def get_unique_transforms_for_upload(self) -> List[Transform]:
        """Get transforms that are ready for upload (not duplicates).
        
        Returns:
            List of unique transforms ready for upload
        """
        with get_db_session() as session:
            transforms = session.query(Transform).filter(
                Transform.status == StatusEnum.COMPLETED,  # type: ignore
                Transform.phash.isnot(None)
            ).all()
            
            unique_transforms = []
            seen_phashes: Set[str] = set()
            
            for transform in transforms:
                if str(transform.phash) not in seen_phashes:
                    # Check if this pHash is similar to any we've already seen
                    is_similar = False
                    for seen_phash in seen_phashes:
                        if self._compare_phashes(str(transform.phash), seen_phash):
                            is_similar = True
                            break
                    
                    if not is_similar:
                        unique_transforms.append(transform)
                        seen_phashes.add(str(transform.phash))
            
            logger.info(f"Found {len(unique_transforms)} unique transforms for upload")
            return unique_transforms


def create_deduplicator() -> Deduplicator:
    """Create and return a deduplicator instance."""
    return Deduplicator()


def check_download_duplicate(ig_post_id: str) -> bool:
    """Check if a download is duplicate by Instagram post ID."""
    deduplicator = create_deduplicator()
    return deduplicator.check_duplicate_download(ig_post_id)


def check_transform_duplicate(transform: Transform) -> Tuple[bool, Optional[str]]:
    """Check if a transform is duplicate by pHash."""
    deduplicator = create_deduplicator()
    return deduplicator.check_duplicate_transform(transform)


def process_all_duplicates() -> List[Transform]:
    """Process all transforms to find and mark duplicates."""
    deduplicator = create_deduplicator()
    return deduplicator.process_transforms_for_duplicates()


def get_unique_transforms() -> List[Transform]:
    """Get all unique transforms ready for upload."""
    deduplicator = create_deduplicator()
    return deduplicator.get_unique_transforms_for_upload()


if __name__ == "__main__":
    # Allow running this module directly for testing
    deduplicator = create_deduplicator()
    stats = deduplicator.get_duplicate_stats()
    print(f"Deduplication stats: {stats}")
    
    # Process duplicates
    duplicates = deduplicator.process_transforms_for_duplicates()
    print(f"Found {len(duplicates)} duplicates")
    
    # Get unique transforms
    unique_transforms = deduplicator.get_unique_transforms_for_upload()
    print(f"Found {len(unique_transforms)} unique transforms")
