"""
Test configuration and fixtures for the YouTube Auto Upload application.
"""

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.db import init_database


@pytest.fixture(scope="session")
def test_db():
    """Create a test database for the session."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Create test database URL
    db_url = f"sqlite:///{db_path}"
    
    # Set environment variable for tests
    os.environ['DB_URL'] = db_url
    
    # Create engine and tables
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    
    yield db_url
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create a database session for each test."""
    from app.db import get_engine, get_session_maker
    
    # Initialize database with test URL
    engine = get_engine()
    SessionMaker = get_session_maker()
    
    session = SessionMaker()
    
    yield session
    
    session.close()


@pytest.fixture(scope="function")
def sample_video_path():
    """Create a sample video file for testing."""
    import tempfile
    from moviepy.editor import ImageClip
    
    # Create a temporary video file
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        # Create a simple video clip
        clip = ImageClip(
            size=(640, 480),
            color=(255, 0, 0),  # Red background
            duration=2.0
        )
        clip.write_videofile(tmp.name, fps=24, verbose=False, logger=None)
        clip.close()
        
        yield tmp.name
        
        # Cleanup
        os.unlink(tmp.name)


@pytest.fixture(scope="function")
def mock_download():
    """Create a mock download object for testing."""
    from app.models import Download, InstagramTarget
    from datetime import datetime
    
    target = InstagramTarget(
        id=1,
        username="test_user",
        is_active=True,
        last_checked=datetime.utcnow()
    )
    
    download = Download(
        id=1,
        target=target,
        ig_post_id="test_post_123",
        ig_shortcode="test_post_123",
        source_url="https://instagram.com/p/test_post_123",
        local_path="test_video.mp4",
        permission_proof_path="test_proof.txt",
        file_size=1024000,  # 1MB
        duration_seconds=30,
        caption="Test caption",
        status="COMPLETED",
        downloaded_at=datetime.utcnow()
    )
    
    return download


@pytest.fixture(scope="function")
def mock_transform():
    """Create a mock transform object for testing."""
    from app.models import Transform
    from datetime import datetime
    
    transform = Transform(
        id=1,
        download_id=1,
        input_path="test_video.mp4",
        output_path="test_output.mp4",
        thumbnail_path="test_thumb.jpg",
        phash="test_phash_123",
        status="COMPLETED",
        transform_duration_seconds=5,
        created_at=datetime.utcnow()
    )
    
    return transform


@pytest.fixture(scope="function")
def youtube_client():
    """Create a YouTube client for testing."""
    from app.youtube_client import YouTubeClient
    
    client = YouTubeClient()
    # Ensure demo mode for tests
    client.settings.demo_mode = True
    
    return client


@pytest.fixture(scope="function")
def video_transformer():
    """Create a video transformer for testing."""
    from app.transform import VideoTransformer
    
    transformer = VideoTransformer()
    # Ensure demo mode for tests
    transformer.settings.demo_mode = True
    
    return transformer


@pytest.fixture(scope="function")
def deduplicator():
    """Create a deduplicator for testing."""
    from app.dedupe import Deduplicator
    
    deduplicator = Deduplicator()
    
    return deduplicator


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set demo mode for all tests
    os.environ['DEMO_MODE'] = 'true'
    os.environ['LOG_LEVEL'] = 'ERROR'  # Reduce log noise in tests
    
    yield
    
    # Cleanup environment variables if needed
    pass
