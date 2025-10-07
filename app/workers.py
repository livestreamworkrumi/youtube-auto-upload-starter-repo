"""
Background workers for processing the video pipeline.

This module handles:
- Download processing from Instagram
- Video transformation
- Deduplication checks
- Upload preparation and approval workflow
- Error handling and retry logic
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db_session, update_system_status
from .dedupe import check_download_duplicate, check_transform_duplicate, process_all_duplicates
from .ig_downloader import InstagramDownloader
from .models import Approval, StatusEnum, Transform, Upload
from .telegram_bot import create_telegram_bot
from .transform import transform_download
from .utils import generate_seo_description, generate_seo_title

logger = logging.getLogger(__name__)


class PipelineWorker:
    """Worker for processing the complete video pipeline."""
    
    def __init__(self):
        self.settings = get_settings()
        self.max_concurrent_jobs = 3
        self.semaphore = asyncio.Semaphore(self.max_concurrent_jobs)
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.settings.is_demo_mode()
    
    async def process_pipeline(self):
        """Process the complete video pipeline."""
        logger.info("Starting video processing pipeline")
        
        try:
            # Step 1: Download new videos from Instagram
            await self._download_new_videos()
            
            # Step 2: Transform downloaded videos
            await self._transform_videos()
            
            # Step 3: Check for duplicates
            await self._process_duplicates()
            
            # Step 4: Create upload records for approval
            await self._create_upload_records()
            
            # Step 5: Process approved uploads
            await self._process_approved_uploads()
            
            logger.info("Video processing pipeline completed")
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            
            # Send error notification
            if not self.is_demo_mode():
                bot = create_telegram_bot()
                await bot.send_error_notification(
                    str(e),
                    "Video processing pipeline"
                )
            
            raise
    
    async def _download_new_videos(self):
        """Download new videos from Instagram targets."""
        logger.info("Starting video downloads")
        
        try:
            # Download from all active targets
            downloader = InstagramDownloader()
            downloads = downloader.download_all_targets()
            
            logger.info(f"Downloaded {len(downloads)} new videos")
            
            # Update system status
            with get_db_session() as session:
                total_downloads = session.query(Transform).count()
                update_system_status(total_downloads=total_downloads)
            
        except Exception as e:
            logger.error(f"Download step failed: {e}")
            raise
    
    async def _transform_videos(self):
        """Transform downloaded videos to YouTube Shorts format."""
        logger.info("Starting video transformations")
        
        try:
            with get_db_session() as session:
                # Get downloads that haven't been transformed yet
                from .models import Download
                untransformed_downloads = session.query(Download).outerjoin(Transform).filter(
                    Transform.id.is_(None)
                ).all()
            
            transformed_count = 0
            
            for download in untransformed_downloads:
                async with self.semaphore:
                    try:
                        transform = await asyncio.get_event_loop().run_in_executor(
                            None, transform_download, download
                        )
                        
                        if transform and transform.status == StatusEnum.COMPLETED:
                            transformed_count += 1
                            logger.info(f"Transformed download {download.id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to transform download {download.id}: {e}")
            
            logger.info(f"Transformed {transformed_count} videos")
            
        except Exception as e:
            logger.error(f"Transform step failed: {e}")
            raise
    
    async def _process_duplicates(self):
        """Process and mark duplicate transforms."""
        logger.info("Starting duplicate processing")
        
        try:
            # Process all transforms for duplicates
            duplicates = await asyncio.get_event_loop().run_in_executor(
                None, process_all_duplicates
            )
            
            logger.info(f"Found and marked {len(duplicates)} duplicate transforms")
            
        except Exception as e:
            logger.error(f"Duplicate processing failed: {e}")
            raise
    
    async def _create_upload_records(self):
        """Create upload records for unique transforms."""
        logger.info("Creating upload records")
        
        try:
            with get_db_session() as session:
                # Get completed transforms that don't have upload records
                transforms = session.query(Transform).outerjoin(Upload).filter(
                    Transform.status == StatusEnum.COMPLETED,
                    Upload.id.is_(None)
                ).all()
            
            created_count = 0
            
            for transform in transforms:
                # Generate SEO content
                title = generate_seo_title(transform.download)
                description = generate_seo_description(transform.download, transform)
                tags = self._generate_tags(transform.download)
                
                # Create upload record
                upload = Upload(
                    transform_id=transform.id,
                    title=title,
                    description=description,
                    tags=tags,
                    status=StatusEnum.PENDING
                )
                
                with get_db_session() as session:
                    session.add(upload)
                    session.commit()
                    session.refresh(upload)
                
                # Create approval record
                approval = Approval(
                    upload_id=upload.id,
                    status=StatusEnum.PENDING
                )
                
                with get_db_session() as session:
                    session.add(approval)
                    session.commit()
                
                # Send preview to admin
                if not self.is_demo_mode():
                    bot = create_telegram_bot()
                    await bot.send_upload_preview(upload, transform)
                
                created_count += 1
                logger.info(f"Created upload record {upload.id}")
            
            logger.info(f"Created {created_count} upload records")
            
        except Exception as e:
            logger.error(f"Upload record creation failed: {e}")
            raise
    
    async def _process_approved_uploads(self):
        """Process approved uploads and upload to YouTube."""
        logger.info("Processing approved uploads")
        
        try:
            with get_db_session() as session:
                # Get approved uploads that haven't been uploaded yet
                approved_uploads = session.query(Upload).join(Approval).filter(
                    Upload.status == StatusEnum.COMPLETED,
                    Approval.status == StatusEnum.COMPLETED
                ).all()
            
            uploaded_count = 0
            
            for upload in approved_uploads:
                async with self.semaphore:
                    try:
                        # Upload to YouTube
                        from .youtube_client import create_youtube_client
                        client = create_youtube_client()
                        
                        tags = upload.tags.split(',') if upload.tags else []
                        
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            client.upload_video,
                            upload.transform,
                            upload.title,
                            upload.description,
                            tags
                        )
                        
                        if result and result.status == StatusEnum.COMPLETED:
                            uploaded_count += 1
                            
                            # Send success notification
                            if not self.is_demo_mode():
                                bot = create_telegram_bot()
                                await bot.send_upload_success_notification(result)
                            
                            logger.info(f"Uploaded video {result.yt_video_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to upload {upload.id}: {e}")
            
            logger.info(f"Uploaded {uploaded_count} videos to YouTube")
            
            # Update system status
            with get_db_session() as session:
                total_uploads = session.query(Upload).filter_by(status=StatusEnum.COMPLETED).count()
                update_system_status(total_uploads=total_uploads)
            
        except Exception as e:
            logger.error(f"Upload processing failed: {e}")
            raise
    
    def _generate_tags(self, download) -> str:
        """Generate tags for YouTube upload."""
        tags = []
        
        # Add creator tag
        tags.append(f"@{download.target.username}")
        
        # Add general tags
        tags.extend([
            "shorts",
            "viral",
            "trending",
            "instagram",
            "repost",
            "creative",
            "viral video"
        ])
        
        # Add content-specific tags based on caption
        if download.caption:
            caption_lower = download.caption.lower()
            if any(word in caption_lower for word in ["funny", "comedy", "joke"]):
                tags.append("funny")
            if any(word in caption_lower for word in ["dance", "dancing", "music"]):
                tags.append("dance")
            if any(word in caption_lower for word in ["cooking", "food", "recipe"]):
                tags.append("cooking")
            if any(word in caption_lower for word in ["fashion", "style", "outfit"]):
                tags.append("fashion")
            if any(word in caption_lower for word in ["travel", "vacation", "trip"]):
                tags.append("travel")
        
        return ','.join(tags[:15])  # YouTube allows max 15 tags


def create_worker() -> PipelineWorker:
    """Create and return a pipeline worker instance."""
    return PipelineWorker()


async def process_pipeline():
    """Process the complete video pipeline."""
    worker = create_worker()
    await worker.process_pipeline()


async def process_downloads_only():
    """Process only the download step."""
    worker = create_worker()
    await worker._download_new_videos()


async def process_transforms_only():
    """Process only the transform step."""
    worker = create_worker()
    await worker._transform_videos()


async def process_uploads_only():
    """Process only approved uploads."""
    worker = create_worker()
    await worker._process_approved_uploads()


if __name__ == "__main__":
    # Allow running this module directly for testing
    import asyncio
    
    async def test_worker():
        worker = create_worker()
        
        if worker.is_demo_mode():
            print("Demo mode: testing worker pipeline")
            await worker.process_pipeline()
            print("Demo pipeline completed")
        else:
            print("Production mode: testing worker pipeline")
            await worker.process_pipeline()
            print("Production pipeline completed")
    
    asyncio.run(test_worker())
