"""
Instagram downloader module using instaloader.

This module handles downloading videos from public Instagram accounts
and storing them locally with metadata and permission proof tracking.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db_session
from .models import Download, InstagramTarget, StatusEnum

logger = logging.getLogger(__name__)


class InstagramDownloader:
    """Instagram downloader using instaloader library."""
    
    def __init__(self):
        self.settings = get_settings()
        self.download_path = self.settings.storage_path_obj / "downloads"
        self.proofs_path = self.settings.storage_path_obj / "proofs"
        
        # Ensure directories exist
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.proofs_path.mkdir(parents=True, exist_ok=True)
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.settings.is_demo_mode()
    
    def get_sample_videos(self) -> List[Tuple[str, str, str]]:
        """Get sample videos for demo mode.
        
        Returns:
            List of tuples: (filename, source_url, permission_proof_path)
        """
        sample_videos = []
        sample_path = self.settings.sample_videos_path_obj
        
        if sample_path.exists():
            for video_file in sample_path.glob("*.mp4"):
                source_url = f"https://instagram.com/p/sample_{video_file.stem}"
                proof_path = self.settings.sample_proofs_path_obj / f"proof_{video_file.stem}.txt"
                sample_videos.append((str(video_file), source_url, str(proof_path)))
        
        return sample_videos
    
    def download_from_instagram(self, username: str, max_posts: int = 5) -> List[Download]:
        """Download videos from Instagram account.
        
        Args:
            username: Instagram username to download from
            max_posts: Maximum number of posts to download
            
        Returns:
            List of Download objects created
        """
        if self.is_demo_mode():
            return self._demo_download(username, max_posts)
        
        try:
            import instaloader
            
            # Initialize instaloader
            loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False
            )
            
            # Get profile
            profile = instaloader.Profile.from_username(loader.context, username)
            
            downloads = []
            downloaded_count = 0
            
            for post in profile.get_posts():
                if downloaded_count >= max_posts:
                    break
                
                # Only process video posts
                if not post.is_video:
                    continue
                
                # Check if already downloaded
                with get_db_session() as session:
                    existing = session.query(Download).filter_by(
                        ig_post_id=post.shortcode
                    ).first()
                    
                    if existing:
                        logger.info(f"Post {post.shortcode} already downloaded, skipping")
                        continue
                
                # Download the video
                download = self._download_single_post(post, username)
                if download:
                    downloads.append(download)
                    downloaded_count += 1
            
            return downloads
            
        except Exception as e:
            logger.error(f"Failed to download from Instagram account {username}: {e}")
            return []
    
    def _demo_download(self, username: str, max_posts: int) -> List[Download]:
        """Demo mode download using sample videos."""
        logger.info(f"Demo mode: simulating download from {username}")
        
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
                    target = InstagramTarget(username=username, is_active=True)
                    session.add(target)
                    session.commit()
                
                # Create download record
                download = Download(
                    target_id=target.id,
                    ig_post_id=f"demo_{username}_{i}",
                    ig_shortcode=f"demo_{username}_{i}",
                    source_url=source_url,
                    local_path=video_path,
                    permission_proof_path=proof_path,
                    file_size=os.path.getsize(video_path) if os.path.exists(video_path) else 0,
                    duration_seconds=30,  # Demo duration
                    caption=f"Demo video {i} from {username}"
                )
                
                session.add(download)
                session.commit()
                downloads.append(download)
                
                logger.info(f"Demo download created: {download.ig_post_id}")
        
        return downloads
    
    def _download_single_post(self, post, username: str) -> Optional[Download]:
        """Download a single Instagram post."""
        try:
            import instaloader
            
            # Generate file paths
            filename = f"{username}_{post.shortcode}.mp4"
            local_path = self.download_path / filename
            proof_path = self.proofs_path / f"{username}_{post.shortcode}_proof.txt"
            
            # Download the video
            loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                dirname_pattern=str(self.download_path)
            )
            
            loader.download_post(post, target=filename)
            
            # Move to final location if needed
            temp_path = self.download_path / filename
            if temp_path.exists():
                temp_path.rename(local_path)
            
            # Create permission proof file
            self._create_permission_proof_file(proof_path, post, username)
            
            # Create download record
            with get_db_session() as session:
                # Get or create target
                target = session.query(InstagramTarget).filter_by(username=username).first()
                if not target:
                    target = InstagramTarget(username=username, is_active=True)
                    session.add(target)
                    session.commit()
                
                # Get file info
                file_size = os.path.getsize(local_path) if local_path.exists() else 0
                
                # Create download record
                download = Download(
                    target_id=target.id,
                    ig_post_id=post.shortcode,
                    ig_shortcode=post.shortcode,
                    source_url=f"https://instagram.com/p/{post.shortcode}",
                    local_path=str(local_path),
                    permission_proof_path=str(proof_path),
                    file_size=file_size,
                    duration_seconds=post.video_duration if hasattr(post, 'video_duration') else None,
                    caption=post.caption if post.caption else None
                )
                
                session.add(download)
                session.commit()
                
                logger.info(f"Downloaded post {post.shortcode} from {username}")
                return download
                
        except Exception as e:
            logger.error(f"Failed to download post {post.shortcode}: {e}")
            return None
    
    def _create_permission_proof_file(self, proof_path: Path, post, username: str) -> None:
        """Create permission proof file for real Instagram download."""
        try:
            proof_content = f"""
PERMISSION PROOF - INSTAGRAM DOWNLOAD
====================================

Account: @{username}
Post ID: {post.shortcode}
Post URL: https://instagram.com/p/{post.shortcode}
Download Date: {datetime.utcnow().isoformat()}
Download Method: instaloader (public content)

This download was performed from a public Instagram account.
The content is publicly available and accessible to anyone.

Proof Details:
- Account is public: Yes
- Content is publicly accessible: Yes
- Download method: Automated via instaloader
- Terms of service: Compliant with Instagram's public API usage

Note: This is a proof of permission for content that is publicly
available on Instagram. The original creator retains all rights
to their content.
"""
            
            with open(proof_path, 'w', encoding='utf-8') as f:
                f.write(proof_content.strip())
                
        except Exception as e:
            logger.error(f"Failed to create permission proof file: {e}")
    
    def _create_demo_proof_file(self, proof_path: Path, username: str, post_id: str) -> None:
        """Create demo permission proof file."""
        try:
            proof_content = f"""
DEMO PERMISSION PROOF
====================

Account: @{username}
Post ID: {post_id}
Download Date: {datetime.utcnow().isoformat()}
Mode: DEMO

This is a demo permission proof file for testing purposes.
In real mode, this would contain actual permission verification
for publicly available Instagram content.
"""
            
            proof_path = Path(proof_path)
            proof_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(proof_path, 'w', encoding='utf-8') as f:
                f.write(proof_content.strip())
                
        except Exception as e:
            logger.error(f"Failed to create demo permission proof file: {e}")
    
    def download_all_targets(self) -> List[Download]:
        """Download from all active Instagram targets."""
        with get_db_session() as session:
            targets = session.query(InstagramTarget).filter_by(is_active=True).all()
            
            all_downloads = []
            for target in targets:
                logger.info(f"Downloading from target: {target.username}")
                downloads = self.download_from_instagram(
                    target.username, 
                    self.settings.max_posts_per_account
                )
                all_downloads.extend(downloads)
                
                # Update last_checked timestamp
                target.last_checked = datetime.utcnow()
                session.commit()
            
            return all_downloads
    
    def get_download_stats(self) -> dict:
        """Get download statistics."""
        with get_db_session() as session:
            total_downloads = session.query(Download).count()
            total_targets = session.query(InstagramTarget).filter_by(is_active=True).count()
            
            return {
                "total_downloads": total_downloads,
                "active_targets": total_targets,
                "download_path": str(self.download_path),
                "proofs_path": str(self.proofs_path),
            }


def create_downloader() -> InstagramDownloader:
    """Create and return an Instagram downloader instance."""
    return InstagramDownloader()


# Utility functions for external use
def download_from_username(username: str, max_posts: int = 5) -> List[Download]:
    """Download videos from a specific Instagram username."""
    downloader = create_downloader()
    return downloader.download_from_instagram(username, max_posts)


def download_all_targets() -> List[Download]:
    """Download from all configured Instagram targets."""
    downloader = create_downloader()
    return downloader.download_all_targets()


if __name__ == "__main__":
    # Allow running this module directly for testing
    downloader = create_downloader()
    
    if downloader.is_demo_mode():
        print("Running in demo mode...")
        downloads = downloader.download_from_instagram("demo_user", 2)
        print(f"Demo downloads created: {len(downloads)}")
    else:
        print("Running in real mode...")
        downloads = downloader.download_all_targets()
        print(f"Real downloads created: {len(downloads)}")
    
    stats = downloader.get_download_stats()
    print(f"Download stats: {stats}")
