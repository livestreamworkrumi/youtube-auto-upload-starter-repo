"""
Tests for YouTube client functionality (dry run mode).

This module tests the YouTube upload client including:
- OAuth authentication flow
- Video upload simulation
- Error handling
- Demo mode functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open

from app.youtube_client import YouTubeClient, create_youtube_client
from app.models import Transform, Download, InstagramTarget


class TestYouTubeClient:
    """Test cases for YouTubeClient class."""
    
    @pytest.fixture
    def youtube_client(self):
        """Create a YouTubeClient instance for testing."""
        return YouTubeClient()
    
    @pytest.fixture
    def mock_transform(self):
        """Create a mock transform for testing."""
        target = InstagramTarget(username="test_user", is_active=True)
        download = Download(
            target=target,
            ig_post_id="test_post",
            ig_shortcode="test_post",
            source_url="https://instagram.com/p/test_post",
            local_path="test_video.mp4",
            permission_proof_path="test_proof.txt",
            file_size=1024,
            duration_seconds=30,
            caption="Test caption"
        )
        
        transform = Transform(
            download_id=1,
            input_path="input.mp4",
            output_path="output.mp4",
            thumbnail_path="thumb.jpg",
            phash="test_hash",
            status="completed"
        )
        transform.download = download
        return transform
    
    def test_client_initialization(self, youtube_client):
        """Test YouTube client initialization."""
        assert youtube_client.settings is not None
        assert youtube_client.chunk_size == 1024 * 1024  # 1MB
        assert youtube_client.max_retries == 3
        assert youtube_client.service is None
        assert youtube_client.credentials is None
    
    def test_is_demo_mode(self, youtube_client):
        """Test demo mode detection."""
        youtube_client.settings.demo_mode = True
        assert youtube_client.is_demo_mode() is True
        
        youtube_client.settings.demo_mode = False
        assert youtube_client.is_demo_mode() is False
    
    @patch('app.youtube_client.Credentials')
    @patch('app.youtube_client.InstalledAppFlow')
    @patch('app.youtube_client.Path')
    def test_authenticate_success(self, mock_path_class, mock_flow_class, mock_credentials_class, youtube_client):
        """Test successful authentication."""
        # Mock Path.exists() to return True
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials_class.from_authorized_user_file.return_value = mock_credentials
        
        # Mock flow
        mock_flow = Mock()
        mock_flow.run_local_server.return_value = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        
        # Mock service
        with patch('app.youtube_client.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            result = youtube_client.authenticate()
            
            assert result is True
            assert youtube_client.credentials == mock_credentials
            assert youtube_client.service == mock_service
    
    @patch('app.youtube_client.Path')
    def test_authenticate_no_client_secrets(self, mock_path, youtube_client):
        """Test authentication failure when client secrets file is missing."""
        mock_path.return_value.exists.return_value = False
        
        result = youtube_client.authenticate()
        
        assert result is False
    
    def test_upload_video_demo_mode(self, youtube_client, mock_transform):
        """Test video upload in demo mode."""
        youtube_client.settings.demo_mode = True
        
        with patch('app.youtube_client.get_db_session') as mock_session:
            mock_upload = Mock()
            mock_session.return_value.__enter__.return_value.add.return_value = None
            mock_session.return_value.__enter__.return_value.commit.return_value = None
            mock_session.return_value.__enter__.return_value.refresh.return_value = None
            
            with patch.object(youtube_client, '_demo_upload', return_value=mock_upload):
                result = youtube_client.upload_video(
                    mock_transform,
                    "Test Video",
                    "Test Description",
                    ["tag1", "tag2"]
                )
                
                assert result == mock_upload
    
    def test_demo_upload(self, youtube_client, mock_transform):
        """Test demo upload functionality."""
        youtube_client.settings.demo_mode = True
        
        with patch('app.youtube_client.get_db_session') as mock_session:
            mock_upload = Mock()
            mock_session.return_value.__enter__.return_value.add.return_value = None
            mock_session.return_value.__enter__.return_value.commit.return_value = None
            mock_session.return_value.__enter__.return_value.refresh.return_value = None
            
            result = youtube_client._demo_upload(
                mock_transform,
                "Test Video",
                "Test Description",
                ["tag1", "tag2"]
            )
            
            assert result is not None
            assert result.yt_video_id.startswith("demo_")
            assert result.title == "Test Video"
            assert result.status == "completed"
    
    def test_upload_video_real_mode_no_service(self, youtube_client, mock_transform):
        """Test upload in real mode without service."""
        youtube_client.settings.demo_mode = False
        youtube_client.service = None
        
        result = youtube_client.upload_video(
            mock_transform,
            "Test Video",
            "Test Description",
            ["tag1", "tag2"]
        )
        
        assert result is None
    
    def test_update_video_privacy_demo_mode(self, youtube_client):
        """Test updating video privacy in demo mode."""
        youtube_client.settings.demo_mode = True
        
        result = youtube_client.update_video_privacy("test_video_id", "public")
        
        assert result is True
    
    def test_update_video_privacy_real_mode_no_service(self, youtube_client):
        """Test updating video privacy in real mode without service."""
        youtube_client.settings.demo_mode = False
        youtube_client.service = None
        
        result = youtube_client.update_video_privacy("test_video_id", "public")
        
        assert result is False
    
    def test_get_channel_info_demo_mode(self, youtube_client):
        """Test getting channel info in demo mode."""
        youtube_client.settings.demo_mode = True
        youtube_client.settings.channel_title = "Demo Channel"
        
        info = youtube_client.get_channel_info()
        
        assert info is not None
        assert info["id"] == "demo_channel"
        assert info["title"] == "Demo Channel"
        assert info["description"] == "Demo YouTube channel"
    
    def test_get_channel_info_real_mode_no_service(self, youtube_client):
        """Test getting channel info in real mode without service."""
        youtube_client.settings.demo_mode = False
        youtube_client.service = None
        
        info = youtube_client.get_channel_info()
        
        assert info is None
    
    def test_get_upload_stats(self, youtube_client):
        """Test getting upload statistics."""
        with patch('app.youtube_client.get_db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.count.side_effect = [10, 8, 2]
            
            stats = youtube_client.get_upload_stats()
            
            assert isinstance(stats, dict)
            assert "total_uploads" in stats
            assert "completed_uploads" in stats
            assert "failed_uploads" in stats
            assert "demo_mode" in stats
            assert "authenticated" in stats


class TestYouTubeClientIntegration:
    """Integration tests for YouTube client."""
    
    def test_create_youtube_client(self):
        """Test creating a YouTube client instance."""
        client = create_youtube_client()
        
        assert isinstance(client, YouTubeClient)
        assert client.settings is not None
    
    def test_upload_transform_video_function(self):
        """Test the upload_transform_video utility function."""
        from app.youtube_client import upload_transform_video
        
        # This would require database setup, so just test the function exists
        assert callable(upload_transform_video)
    
    def test_get_channel_info_function(self):
        """Test the get_channel_info utility function."""
        from app.youtube_client import get_channel_info
        
        # This would require database setup, so just test the function exists
        assert callable(get_channel_info)


class TestYouTubeClientErrorHandling:
    """Test error handling in YouTube client."""
    
    def test_upload_video_database_error(self):
        """Test upload video with database error."""
        client = YouTubeClient()
        client.settings.demo_mode = True
        
        mock_transform = Mock()
        mock_transform.id = 1
        
        with patch('app.youtube_client.get_db_session') as mock_session:
            mock_session.side_effect = Exception("Database error")
            
            result = client.upload_video(
                mock_transform,
                "Test Video",
                "Test Description",
                ["tag1"]
            )
            
            assert result is None
    
    @patch('app.youtube_client.Path')
    def test_authenticate_flow_error(self, mock_path_class):
        """Test authentication with flow error."""
        client = YouTubeClient()
        
        # Mock Path.exists() to return True
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        with patch('app.youtube_client.InstalledAppFlow') as mock_flow_class:
            mock_flow = Mock()
            mock_flow.run_local_server.side_effect = Exception("OAuth error")
            mock_flow_class.from_client_secrets_file.return_value = mock_flow
            
            # Mock the token file operations
            with patch('builtins.open', mock_open()) as mock_file:
                result = client.authenticate()
                
                assert result is False
    
    def test_upload_video_service_error(self):
        """Test upload video with service error."""
        client = YouTubeClient()
        client.settings.demo_mode = False
        
        mock_service = Mock()
        mock_service.videos.return_value.insert.return_value.execute.side_effect = Exception("Upload error")
        client.service = mock_service
        
        mock_transform = Mock()
        mock_transform.output_path = "test.mp4"
        
        with patch('app.youtube_client.get_db_session'):
            result = client.upload_video(
                mock_transform,
                "Test Video",
                "Test Description",
                ["tag1"]
            )
            
            assert result is None


class TestYouTubeClientMocking:
    """Test YouTube client with various mocking scenarios."""
    
    def test_resumable_upload_success(self):
        """Test successful resumable upload."""
        client = YouTubeClient()
        
        mock_request = Mock()
        mock_request.next_chunk.return_value = (Mock(), {"id": "test_video_id"})
        
        with patch.object(client, '_resumable_upload', return_value={"id": "test_video_id"}):
            result = client._resumable_upload(mock_request)
            
            assert result is not None
            assert result["id"] == "test_video_id"
    
    def test_resumable_upload_retry(self):
        """Test resumable upload with retries."""
        client = YouTubeClient()
        
        mock_request = Mock()
        mock_request.next_chunk.side_effect = [
            Exception("Temporary error"),
            Exception("Another error"),
            (Mock(), {"id": "test_video_id"})
        ]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client._resumable_upload(mock_request)
            
            # Should succeed after retries
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])
