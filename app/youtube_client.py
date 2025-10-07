"""
YouTube upload client with OAuth authentication and resumable uploads.

This module handles:
- OAuth 2.0 authentication flow
- Resumable video uploads to YouTube
- Video metadata management
- Error handling and retry logic
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .config import get_settings
from .db import get_db_session
from .models import Transform, Upload, StatusEnum

logger = logging.getLogger(__name__)

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeClient:
    """YouTube upload client with OAuth and resumable uploads."""
    
    def __init__(self):
        self.settings = get_settings()
        self.service = None
        self.credentials = None
        
        # Upload settings
        self.chunk_size = self.settings.youtube_upload_chunk_size
        self.max_retries = self.settings.youtube_max_retry_attempts
        
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.settings.is_demo_mode()
    
    def authenticate(self) -> bool:
        """Authenticate with YouTube API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if self.is_demo_mode():
            logger.info("Demo mode: skipping YouTube authentication")
            return True
        
        try:
            # Load existing credentials
            token_path = Path(self.settings.token_file)
            credentials = None
            
            if token_path.exists():
                credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            
            # If there are no valid credentials, authenticate
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    client_secrets_path = Path(self.settings.youtube_client_secrets)
                    if not client_secrets_path.exists():
                        logger.error(f"Client secrets file not found: {client_secrets_path}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(client_secrets_path), SCOPES
                    )
                    credentials = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(credentials.to_json())
            
            self.credentials = credentials
            
            # Build YouTube service
            self.service = build('youtube', 'v3', credentials=credentials)
            
            logger.info("YouTube authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            return False
    
    def upload_video(
        self, 
        transform: Transform, 
        title: str, 
        description: str, 
        tags: List[str]
    ) -> Optional[Upload]:
        """Upload a transformed video to YouTube.
        
        Args:
            transform: Transform record containing video path
            title: Video title
            description: Video description
            tags: List of video tags
            
        Returns:
            Upload record or None if failed
        """
        if self.is_demo_mode():
            return self._demo_upload(transform, title, description, tags)
        
        if not self.service:
            if not self.authenticate():
                logger.error("YouTube service not available")
                return None
        
        try:
            # Create upload record
            with get_db_session() as session:
                upload = Upload(
                    transform_id=transform.id,
                    title=title,
                    description=description,
                    tags=json.dumps(tags) if tags else None,
                    status=StatusEnum.IN_PROGRESS
                )
                session.add(upload)
                session.commit()
                session.refresh(upload)
            
            # Prepare video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '22',  # People & Blogs category
                    'defaultLanguage': 'en',
                    'defaultAudioLanguage': 'en'
                },
                'status': {
                    'privacyStatus': 'private',  # Upload as private initially
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Create media upload object
            media = MediaFileUpload(
                transform.output_path,
                chunksize=self.chunk_size,
                resumable=True
            )
            
            # Start upload
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute upload with retry logic
            response = self._resumable_upload(insert_request)
            
            if response:
                # Extract video ID
                video_id = response['id']
                
                # Update upload record
                with get_db_session() as session:
                    db_upload = session.query(Upload).filter_by(id=upload.id).first()
                    if db_upload:
                        db_upload.yt_video_id = video_id
                        db_upload.status = StatusEnum.COMPLETED
                        db_upload.uploaded_at = datetime.utcnow()  # type: ignore
                        session.commit()
                
                logger.info(f"Video uploaded successfully: {video_id}")
                return upload
            else:
                # Mark upload as failed
                with get_db_session() as session:
                    db_upload = session.query(Upload).filter_by(id=upload.id).first()
                    if db_upload:
                        db_upload.status = StatusEnum.FAILED
                        db_upload.error_message = "Upload failed after retries"  # type: ignore
                        session.commit()
                
                logger.error(f"Video upload failed for transform {transform.id}")
                return None
                
        except Exception as e:
            logger.error(f"YouTube upload error: {e}")
            
            # Update upload record with error
            try:
                with get_db_session() as session:
                    db_upload = session.query(Upload).filter_by(id=upload.id).first()
                    if db_upload:
                        db_upload.status = StatusEnum.FAILED
                        db_upload.error_message = str(e)  # type: ignore
                        session.commit()
            except:
                pass
            
            return None
    
    def _resumable_upload(self, insert_request) -> Optional[Dict]:
        """Execute resumable upload with retry logic."""
        response = None
        error = None
        
        for attempt in range(self.max_retries):
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        return response
                    else:
                        raise HttpError(resp=None, content=f"Upload failed: {response}")
                else:
                    logger.info(f"Upload progress: {status.progress() * 100:.1f}%")
                    
            except HttpError as e:
                error = e
                if e.resp.status in [500, 502, 503, 504]:
                    # Retry on server errors
                    logger.warning(f"Server error during upload (attempt {attempt + 1}): {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    # Don't retry on client errors
                    logger.error(f"Client error during upload: {e}")
                    break
            except Exception as e:
                error = e
                logger.error(f"Unexpected error during upload (attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)
        
        logger.error(f"Upload failed after {self.max_retries} attempts: {error}")
        return None
    
    def _demo_upload(
        self, 
        transform: Transform, 
        title: str, 
        description: str, 
        tags: List[str]
    ) -> Optional[Upload]:
        """Demo mode upload simulation."""
        logger.info(f"Demo mode: simulating upload of {title}")
        
        try:
            # Simulate upload delay
            time.sleep(1)
            
            # Create upload record
            with get_db_session() as session:
                upload = Upload(
                    transform_id=transform.id,
                    yt_video_id=f"demo_{transform.id}_{int(time.time())}",
                    title=title,
                    description=description,
                    tags=json.dumps(tags) if tags else None,
                    status=StatusEnum.COMPLETED,
                    uploaded_at=datetime.utcnow()
                )
                session.add(upload)
                session.commit()
                session.refresh(upload)
            
            logger.info(f"Demo upload completed: {upload.yt_video_id}")
            return upload
            
        except Exception as e:
            logger.error(f"Demo upload error: {e}")
            return None
    
    def update_video_privacy(self, video_id: str, privacy_status: str = 'public') -> bool:
        """Update video privacy status.
        
        Args:
            video_id: YouTube video ID
            privacy_status: 'public', 'private', or 'unlisted'
            
        Returns:
            True if successful, False otherwise
        """
        if self.is_demo_mode():
            logger.info(f"Demo mode: simulating privacy update for {video_id} to {privacy_status}")
            return True
        
        if not self.service:
            logger.error("YouTube service not available")
            return False
        
        try:
            body = {
                'id': video_id,
                'status': {
                    'privacyStatus': privacy_status
                }
            }
            
            response = self.service.videos().update(
                part='status',
                body=body
            ).execute()
            
            logger.info(f"Video {video_id} privacy updated to {privacy_status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update video privacy: {e}")
            return False
    
    def get_channel_info(self) -> Optional[Dict]:
        """Get YouTube channel information.
        
        Returns:
            Channel info dictionary or None if failed
        """
        if self.is_demo_mode():
            return {
                "id": "demo_channel",
                "title": self.settings.channel_title,
                "description": "Demo YouTube channel",
                "subscriberCount": "1000",
                "videoCount": "50"
            }
        
        if not self.service:
            logger.error("YouTube service not available")
            return None
        
        try:
            response = self.service.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()
            
            if response['items']:
                channel = response['items'][0]
                return {
                    "id": channel['id'],
                    "title": channel['snippet']['title'],
                    "description": channel['snippet']['description'],
                    "subscriberCount": channel['statistics'].get('subscriberCount', '0'),
                    "videoCount": channel['statistics'].get('videoCount', '0')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return None
    
    def get_upload_stats(self) -> Dict:
        """Get upload statistics."""
        with get_db_session() as session:
            total_uploads = session.query(Upload).count()
            completed_uploads = session.query(Upload).filter_by(
                status=StatusEnum.COMPLETED
            ).count()
            failed_uploads = session.query(Upload).filter_by(
                status=StatusEnum.FAILED
            ).count()
            
            return {
                "total_uploads": total_uploads,
                "completed_uploads": completed_uploads,
                "failed_uploads": failed_uploads,
                "demo_mode": self.is_demo_mode(),
                "authenticated": self.service is not None or self.is_demo_mode(),
            }


def create_youtube_client() -> YouTubeClient:
    """Create and return a YouTube client instance."""
    client = YouTubeClient()
    if not client.is_demo_mode():
        client.authenticate()
    return client


def upload_transform_video(
    transform: Transform, 
    title: str, 
    description: str, 
    tags: List[str]
) -> Optional[Upload]:
    """Upload a transformed video to YouTube."""
    client = create_youtube_client()
    return client.upload_video(transform, title, description, tags)


def get_channel_info() -> Optional[Dict]:
    """Get YouTube channel information."""
    client = create_youtube_client()
    return client.get_channel_info()


if __name__ == "__main__":
    # Allow running this module directly for testing
    client = create_youtube_client()
    
    if client.is_demo_mode():
        print("Running in demo mode")
        channel_info = client.get_channel_info()
        print(f"Demo channel info: {channel_info}")
    else:
        print("Running in real mode")
        if client.authenticate():
            channel_info = client.get_channel_info()
            print(f"Channel info: {channel_info}")
        else:
            print("Authentication failed")
    
    stats = client.get_upload_stats()
    print(f"Upload stats: {stats}")
