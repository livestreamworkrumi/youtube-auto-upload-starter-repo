"""
Instagram video downloader module for the YouTube Auto Upload application.

This module handles:
- Downloading videos from public Instagram accounts
- Managing Instagram targets
- Permission proof tracking
- Demo mode simulation
"""

import logging
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .config import get_settings
from .db import get_db_session
from .models import Download, InstagramTarget, PermissionProof, StatusEnum

logger = logging.getLogger(__name__)


class InstagramDownloader:
    """Instagram video downloader with demo mode support."""
    
    def __init__(self):
        self.settings = get_settings()
        self.storage_path = self.settings.storage_path_obj / "downloads"
        self.proofs_path = self.settings.storage_path_obj / "proofs"
        
        # Ensure directories exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.proofs_path.mkdir(parents=True, exist_ok=True)
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.settings.demo_mode
    
    def download_from_instagram(self, username: str, max_posts: int = 3) -> List[Download]:
        """Download videos from a specific Instagram account.
        
        Args:
            username: Instagram username (without @)
            max_posts: Maximum number of posts to download
            
        Returns:
            List of Download records
        """
        if self.is_demo_mode():
            return self._demo_download(username, max_posts)
        
        # Real Instagram download implementation would go here
        # For now, return empty list
        logger.info(f"Real mode: Instagram download not implemented for @{username}")
        return []
    
    def _demo_download(self, username: str, max_posts: int) -> List[Download]:
        """Demo mode download simulation."""
        logger.info(f"Demo mode: downloading from @{username}")
        
        # Get sample videos for demo
        sample_videos = self.get_sample_videos()
        downloads = []
        
        for i, (video_path, source_url, proof_path) in enumerate(sample_videos[:max_posts]):
            # Create demo permission proof file
            self._create_demo_proof_file(Path(proof_path), username, f"demo_post_{i}")
            
            # Create download record
            with get_db_session() as session:
                # Get or create target
                target = session.query(InstagramTarget).filter_by(username=username).first()
                if not target:
                    target = InstagramTarget(
                        username=username,
                        is_active=True,
                        last_checked=datetime.utcnow()
                    )
                    session.add(target)
                    session.commit()
                    session.refresh(target)
                
                # Create download record
                download = Download(
                    target_id=target.id,
                    ig_shortcode=f"demo_{username}_{i}",
                    source_url=source_url,
                    local_path=video_path,
                    permission_proof_path=proof_path,
                    caption=f"Demo video {i+1} from @{username}",
                    duration=random.randint(15, 60),
                    file_size=random.randint(1024*1024, 10*1024*1024),  # 1MB to 10MB
                    status=StatusEnum.COMPLETED,
                    downloaded_at=datetime.utcnow()
                )
                session.add(download)
                session.commit()
                session.refresh(download)
                
                downloads.append(download)
        
        logger.info(f"Demo download completed: {len(downloads)} videos from @{username}")
        return downloads
    
    def download_all_targets(self) -> List[Download]:
        """Download videos from all active Instagram targets.
        
        Returns:
            List of Download records from all targets
        """
        if self.is_demo_mode():
            return self._demo_download_all()
        
        with get_db_session() as session:
            targets = session.query(InstagramTarget).filter_by(is_active=True).all()
            
            all_downloads = []
            for target in targets:
                logger.info(f"Downloading from target: {target.username}")
                downloads = self.download_from_instagram(
                    str(target.username), 
                    self.settings.max_posts_per_account
                )
                all_downloads.extend(downloads)
                
                # Update last_checked timestamp
                target.last_checked = datetime.utcnow()  # type: ignore
                session.commit()
            
            return all_downloads
    
    def _demo_download_all(self) -> List[Download]:
        """Demo mode download from all targets."""
        logger.info("Demo mode: downloading from all targets")
        
        # Get demo targets
        demo_targets = ["demo_user1", "demo_user2", "demo_user3"]
        all_downloads = []
        
        for username in demo_targets:
            downloads = self._demo_download(username, 2)  # 2 videos per target
            all_downloads.extend(downloads)
        
        return all_downloads
    
    def get_sample_videos(self) -> List[Tuple[str, str, str]]:
        """Get list of sample videos for demo mode.
        
        Returns:
            List of tuples (video_path, source_url, proof_path)
        """
        sample_dir = Path("sample_videos")
        if not sample_dir.exists():
            # Create sample directory if it doesn't exist
            sample_dir.mkdir(exist_ok=True)
        
        sample_videos = []
        for i in range(5):  # 5 sample videos
            video_path = str(sample_dir / f"sample_video_{i+1}.mp4")
            source_url = f"https://instagram.com/p/sample_{i+1}"
            proof_path = str(self.proofs_path / f"proof_sample_{i+1}.txt")
            sample_videos.append((video_path, source_url, proof_path))
        
        return sample_videos
    
    def _create_demo_proof_file(self, proof_path: Path, username: str, post_id: str) -> None:
        """Create a demo permission proof file."""
        try:
            proof_path.parent.mkdir(parents=True, exist_ok=True)
            
            proof_content = f"""PERMISSION PROOF
================

Username: @{username}
Post ID: {post_id}
Date: {datetime.utcnow().isoformat()}
Type: Public Instagram Content
Status: Permission Granted

This content was downloaded from a public Instagram account.
The account owner has made this content publicly available.
No private or restricted content was accessed.

Demo Mode: This is a simulated permission proof for testing purposes.
"""
            
            with open(proof_path, 'w') as f:
                f.write(proof_content)
                
        except Exception as e:
            logger.error(f"Failed to create demo proof file: {e}")
    
    def add_target(self, username: str) -> bool:
        """Add a new Instagram target.
        
        Args:
            username: Instagram username (without @)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                # Check if target already exists
                existing = session.query(InstagramTarget).filter_by(username=username).first()
                if existing:
                    logger.warning(f"Target @{username} already exists")
                    return False
                
                # Create new target
                target = InstagramTarget(
                    username=username,
                    is_active=True,
                    last_checked=datetime.utcnow()
                )
                session.add(target)
                session.commit()
                
                logger.info(f"Added new target: @{username}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add target @{username}: {e}")
            return False
    
    def remove_target(self, username: str) -> bool:
        """Remove an Instagram target.
        
        Args:
            username: Instagram username (without @)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                target = session.query(InstagramTarget).filter_by(username=username).first()
                if not target:
                    logger.warning(f"Target @{username} not found")
                    return False
                
                # Deactivate instead of deleting to preserve history
                target.is_active = False
                session.commit()
                
                logger.info(f"Removed target: @{username}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove target @{username}: {e}")
            return False
    
    def get_targets(self) -> List[InstagramTarget]:
        """Get all Instagram targets.
        
        Returns:
            List of InstagramTarget records
        """
        with get_db_session() as session:
            return session.query(InstagramTarget).all()
    
    def get_download_stats(self) -> dict:
        """Get download statistics.
        
        Returns:
            Dictionary with download statistics
        """
        with get_db_session() as session:
            total_downloads = session.query(Download).count()
            completed_downloads = session.query(Download).filter_by(
                status=StatusEnum.COMPLETED
            ).count()
            failed_downloads = session.query(Download).filter_by(
                status=StatusEnum.FAILED
            ).count()
            
            total_targets = session.query(InstagramTarget).count()
            active_targets = session.query(InstagramTarget).filter_by(
                is_active=True
            ).count()
            
            return {
                "total_downloads": total_downloads,
                "completed_downloads": completed_downloads,
                "failed_downloads": failed_downloads,
                "total_targets": total_targets,
                "active_targets": active_targets,
                "demo_mode": self.is_demo_mode()
            }


def create_instagram_downloader() -> InstagramDownloader:
    """Create and return an Instagram downloader instance."""
    return InstagramDownloader()


if __name__ == "__main__":
    # Test the downloader
    downloader = create_instagram_downloader()
    
    print("Instagram Downloader Test")
    print("=" * 30)
    
    if downloader.is_demo_mode():
        print("Running in demo mode")
        
        # Test downloading from all targets
        downloads = downloader.download_all_targets()
        print(f"Downloaded {len(downloads)} videos")
        
        # Test adding a target
        success = downloader.add_target("test_user")
        print(f"Added target: {success}")
        
        # Get stats
        stats = downloader.get_download_stats()
        print(f"Download stats: {stats}")
    else:
        print("Running in real mode")
        print("Real Instagram integration not implemented")
    
    print("Test completed")
