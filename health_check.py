#!/usr/bin/env python3
"""
Health check script for the YouTube Auto Upload application.
This script verifies that the application can start up correctly.
"""

import sys
import os

def main():
    """Run health checks for the application."""
    try:
        # Set demo mode for health check
        os.environ['DEMO_MODE'] = 'true'
        os.environ['LOG_LEVEL'] = 'ERROR'  # Reduce log noise
        
        print("🔍 Running health checks...")
        
        # Test 1: Import main modules
        print("✅ Testing imports...")
        from app.config import get_settings
        from app.db import init_database
        from app.models import Base, create_tables
        from app.ig_downloader import InstagramDownloader
        from app.transform import VideoTransformer
        from app.dedupe import Deduplicator
        from app.youtube_client import YouTubeClient
        
        # Test 2: Configuration
        print("✅ Testing configuration...")
        settings = get_settings()
        assert settings.demo_mode == True, "Demo mode should be enabled"
        print(f"   Demo mode: {settings.demo_mode}")
        print(f"   Log level: {settings.log_level}")
        
        # Test 3: Database initialization
        print("✅ Testing database initialization...")
        init_database()
        print("   Database initialized successfully")
        
        # Test 4: Model creation
        print("✅ Testing model creation...")
        from app.db import get_engine
        engine = get_engine()
        create_tables(engine)
        print("   Database tables created successfully")
        
        # Test 5: Component initialization
        print("✅ Testing component initialization...")
        downloader = InstagramDownloader()
        transformer = VideoTransformer()
        deduplicator = Deduplicator()
        youtube_client = YouTubeClient()
        print("   All components initialized successfully")
        
        # Test 6: Demo mode functionality
        print("✅ Testing demo mode functionality...")
        downloads = downloader.download_all_targets()
        print(f"   Downloaded {len(downloads)} demo videos")
        
        print("\n🎉 All health checks passed!")
        print("✅ Application is ready for deployment")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
