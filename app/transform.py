"""
Video transformation module for converting Instagram videos to YouTube Shorts format.

This module handles:
- Converting videos to 9:16 aspect ratio (1080x1920)
- Adding intro and outro videos
- Overlaying credit text and subscribe CTA
- Generating thumbnails
- Computing perceptual hashes for deduplication
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import imagehash
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    CompositeVideoClip, ImageClip, TextClip, VideoFileClip, 
    concatenate_videoclips
)

from .config import get_settings
from .db import get_db_session
from .models import Download, Transform, StatusEnum

logger = logging.getLogger(__name__)


class VideoTransformer:
    """Video transformation pipeline for YouTube Shorts."""
    
    def __init__(self):
        self.settings = get_settings()
        self.output_path = self.settings.storage_path_obj / "transforms"
        self.thumbnails_path = self.settings.storage_path_obj / "thumbnails"
        
        # Ensure directories exist
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.thumbnails_path.mkdir(parents=True, exist_ok=True)
        
        # Target resolution for YouTube Shorts
        self.target_width, self.target_height = self.settings.target_resolution
    
    def transform_video(self, download: Download) -> Optional[Transform]:
        """Transform a downloaded video to YouTube Shorts format.
        
        Args:
            download: Download record to transform
            
        Returns:
            Transform record or None if failed
        """
        try:
            logger.info(f"Starting transformation for download {download.id}")
            
            # Create transform record
            with get_db_session() as session:
                transform = Transform(
                    download_id=download.id,
                    input_path=download.local_path,
                    output_path="",  # Will be set after processing
                    thumbnail_path="",  # Will be set after processing
                    status=StatusEnum.IN_PROGRESS
                )
                session.add(transform)
                session.commit()
                session.refresh(transform)
            
            # Generate output paths
            output_filename = f"transform_{transform.id}_{download.ig_shortcode}.mp4"
            thumbnail_filename = f"thumb_{transform.id}_{download.ig_shortcode}.jpg"
            
            output_path = self.output_path / output_filename
            thumbnail_path = self.thumbnails_path / thumbnail_filename
            
            # Process the video
            success = self._process_video(
                input_path=str(download.local_path),
                output_path=output_path,
                thumbnail_path=thumbnail_path,
                ig_username=download.target.username,
                ig_shortcode=str(download.ig_shortcode)
            )
            
            if success:
                # Generate perceptual hash
                phash = self._compute_phash(output_path)
                
                # Update transform record
                with get_db_session() as session:
                    db_transform = session.query(Transform).filter_by(id=transform.id).first()
                    if db_transform:
                        db_transform.output_path = str(output_path)  # type: ignore
                        db_transform.thumbnail_path = str(thumbnail_path)  # type: ignore
                        db_transform.phash = phash  # type: ignore
                        db_transform.status = StatusEnum.COMPLETED  # type: ignore
                        session.commit()
                
                logger.info(f"Transformation completed for download {download.id}")
                return transform
            else:
                # Mark as failed
                with get_db_session() as session:
                    db_transform = session.query(Transform).filter_by(id=transform.id).first()
                    if db_transform:
                        db_transform.status = StatusEnum.FAILED  # type: ignore
                        db_transform.error_message = "Video processing failed"  # type: ignore
                        session.commit()
                
                logger.error(f"Transformation failed for download {download.id}")
                return None
                
        except Exception as e:
            logger.error(f"Transform error for download {download.id}: {e}")
            
            # Update transform record with error
            try:
                with get_db_session() as session:
                    db_transform = session.query(Transform).filter_by(id=transform.id).first()
                    if db_transform:
                        db_transform.status = StatusEnum.FAILED  # type: ignore
                        db_transform.error_message = str(e)  # type: ignore
                        session.commit()
            except:
                pass
            
            return None
    
    def _process_video(
        self, 
        input_path: str, 
        output_path: Path, 
        thumbnail_path: Path,
        ig_username: str,
        ig_shortcode: str
    ) -> bool:
        """Process video with MoviePy.
        
        Args:
            input_path: Path to input video
            output_path: Path for output video
            thumbnail_path: Path for thumbnail image
            ig_username: Instagram username for credit
            ig_shortcode: Instagram post shortcode
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load input video
            video = VideoFileClip(input_path)
            
            # Resize to target aspect ratio (9:16)
            video_resized = self._resize_to_aspect_ratio(video)
            
            # Add intro and outro if available
            final_video = self._add_intro_outro(video_resized)
            
            # Add overlays (credit text and subscribe CTA)
            final_video = self._add_overlays(final_video, ig_username)
            
            # Write output video
            final_video.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            # Generate thumbnail
            self._generate_thumbnail(final_video, thumbnail_path)
            
            # Clean up
            video.close()
            final_video.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Video processing error: {e}")
            return False
    
    def _resize_to_aspect_ratio(self, video: VideoFileClip) -> VideoFileClip:
        """Resize video to 9:16 aspect ratio (1080x1920)."""
        try:
            # Calculate dimensions to maintain aspect ratio and fit in target size
            video_w, video_h = video.size
            target_w, target_h = self.target_width, self.target_height
            
            # Calculate scaling factor to fit video in target dimensions
            scale_w = target_w / video_w
            scale_h = target_h / video_h
            
            # Use the smaller scale to ensure video fits within target dimensions
            scale = min(scale_w, scale_h)
            
            new_w = int(video_w * scale)
            new_h = int(video_h * scale)
            
            # Resize video
            video_resized = video.resize((new_w, new_h))
            
            # Create background clip with target dimensions
            background = ImageClip(
                size=(target_w, target_h),
                color=(0, 0, 0),  # Black background
                duration=video_resized.duration
            )
            
            # Center the resized video on the background
            video_centered = video_resized.set_position('center')
            
            # Composite the video on the background
            final_video = CompositeVideoClip([background, video_centered])
            
            return final_video
            
        except Exception as e:
            logger.error(f"Error resizing video: {e}")
            return video
    
    def _add_intro_outro(self, video: VideoFileClip) -> VideoFileClip:
        """Add intro and outro videos if available."""
        try:
            clips = []
            
            # Add intro if available
            intro_path = Path(self.settings.branded_intro)
            if intro_path.exists():
                try:
                    intro = VideoFileClip(str(intro_path))
                    clips.append(intro)
                    logger.info("Added intro video")
                except Exception as e:
                    logger.warning(f"Could not load intro video: {e}")
            
            # Add main video
            clips.append(video)
            
            # Add outro if available
            outro_path = Path(self.settings.branded_outro)
            if outro_path.exists():
                try:
                    outro = VideoFileClip(str(outro_path))
                    clips.append(outro)
                    logger.info("Added outro video")
                except Exception as e:
                    logger.warning(f"Could not load outro video: {e}")
            
            # Concatenate all clips
            if len(clips) > 1:
                final_video = concatenate_videoclips(clips)
                return final_video
            else:
                return video
                
        except Exception as e:
            logger.error(f"Error adding intro/outro: {e}")
            return video
    
    def _add_overlays(self, video: VideoFileClip, ig_username: str) -> VideoFileClip:
        """Add credit text and subscribe CTA overlays."""
        try:
            clips = [video]
            
            # Add credit text overlay
            credit_text = f"Credit: @{ig_username}"
            credit_clip = TextClip(
                credit_text,
                fontsize=24,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2
            ).set_position(('left', 'bottom')).set_duration(video.duration).set_start(0)
            
            clips.append(credit_clip)
            
            # Add subscribe CTA (simple text for now)
            subscribe_text = "Subscribe for more!"
            subscribe_clip = TextClip(
                subscribe_text,
                fontsize=20,
                color='red',
                font='Arial-Bold',
                stroke_color='white',
                stroke_width=1
            ).set_position(('right', 'top')).set_duration(video.duration).set_start(0)
            
            clips.append(subscribe_clip)
            
            # Composite all clips
            final_video = CompositeVideoClip(clips)
            return final_video
            
        except Exception as e:
            logger.error(f"Error adding overlays: {e}")
            return video
    
    def _generate_thumbnail(self, video: VideoFileClip, thumbnail_path: Path) -> bool:
        """Generate thumbnail from video."""
        try:
            # Take frame at 1 second or middle of video
            frame_time = min(1.0, video.duration / 2)
            
            # Save frame as image
            video.save_frame(str(thumbnail_path), t=frame_time)
            
            # Resize thumbnail to standard size
            with Image.open(thumbnail_path) as img:
                img_resized = img.resize((480, 854))  # 9:16 aspect ratio
                img_resized.save(thumbnail_path, 'JPEG', quality=85)
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return False
    
    def _compute_phash(self, video_path: Path) -> Optional[str]:
        """Compute perceptual hash for video deduplication."""
        try:
            # Extract frame at 1 second
            with VideoFileClip(str(video_path)) as video:
                frame_time = min(1.0, video.duration / 2)
                video.save_frame('temp_frame.jpg', t=frame_time)
            
            # Compute hash from frame
            with Image.open('temp_frame.jpg') as img:
                hash_value = imagehash.phash(img)
            
            # Clean up temp file
            if os.path.exists('temp_frame.jpg'):
                os.remove('temp_frame.jpg')
            
            return str(hash_value)
            
        except Exception as e:
            logger.error(f"Error computing pHash: {e}")
            return None
    
    def get_transform_stats(self) -> dict:
        """Get transformation statistics."""
        with get_db_session() as session:
            total_transforms = session.query(Transform).count()
            completed_transforms = session.query(Transform).filter_by(
                status=StatusEnum.COMPLETED
            ).count()
            failed_transforms = session.query(Transform).filter_by(
                status=StatusEnum.FAILED
            ).count()
            
            return {
                "total_transforms": total_transforms,
                "completed_transforms": completed_transforms,
                "failed_transforms": failed_transforms,
                "output_path": str(self.output_path),
                "thumbnails_path": str(self.thumbnails_path),
            }


def create_transformer() -> VideoTransformer:
    """Create and return a video transformer instance."""
    return VideoTransformer()


def transform_download(download: Download) -> Optional[Transform]:
    """Transform a single download."""
    transformer = create_transformer()
    return transformer.transform_video(download)


def transform_all_pending() -> list:
    """Transform all pending downloads."""
    transformer = create_transformer()
    transforms = []
    
    with get_db_session() as session:
        # Get downloads that haven't been transformed yet
        downloads = session.query(Download).outerjoin(Transform).filter(
            Transform.id.is_(None)
        ).all()
        
        for download in downloads:
            transform = transformer.transform_video(download)
            if transform:
                transforms.append(transform)
    
    return transforms


def create_mock_video() -> VideoFileClip:
    """Create a mock video for testing purposes."""
    try:
        # Create a simple colored clip for testing
        return ImageClip(
            size=(640, 480),
            color=(255, 0, 0),  # Red background
            duration=5.0
        )
    except Exception as e:
        logger.error(f"Error creating mock video: {e}")
        # Return a minimal clip
        return ImageClip(
            size=(100, 100),
            color=(0, 0, 0),
            duration=1.0
        )


if __name__ == "__main__":
    # Allow running this module directly for testing
    transformer = create_transformer()
    stats = transformer.get_transform_stats()
    print(f"Transform stats: {stats}")
