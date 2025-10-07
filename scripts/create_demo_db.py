#!/usr/bin/env python3
"""
Create demo database with sample data for testing.

This script populates the database with sample data for demo mode testing,
including sample Instagram targets, downloads, transforms, and uploads.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.db import init_database, get_db_session
from app.models import (
    InstagramTarget, Download, Transform, Upload, Approval, 
    Permission, LogEntry, SystemStatus, StatusEnum
)


def create_demo_targets():
    """Create demo Instagram targets."""
    print("📱 Creating demo Instagram targets...")
    
    demo_targets = [
        {"username": "demo_creator1", "is_active": True},
        {"username": "demo_creator2", "is_active": True},
        {"username": "demo_creator3", "is_active": False},
    ]
    
    with get_db_session() as session:
        for target_data in demo_targets:
            # Check if target already exists
            existing = session.query(InstagramTarget).filter_by(
                username=target_data["username"]
            ).first()
            
            if not existing:
                target = InstagramTarget(
                    username=target_data["username"],
                    is_active=target_data["is_active"],
                    last_checked=datetime.utcnow() - timedelta(hours=2)
                )
                session.add(target)
                session.commit()
                print(f"  ✅ Created target: @{target_data['username']}")
            else:
                print(f"  ⚠️  Target already exists: @{target_data['username']}")


def create_demo_downloads():
    """Create demo download records."""
    print("📥 Creating demo downloads...")
    
    with get_db_session() as session:
        targets = session.query(InstagramTarget).all()
        
        for i, target in enumerate(targets[:2]):  # Only for first 2 targets
            # Create 2 downloads per target
            for j in range(2):
                download_id = f"demo_{target.username}_{j}"
                
                # Check if download already exists
                existing = session.query(Download).filter_by(
                    ig_post_id=download_id
                ).first()
                
                if not existing:
                    download = Download(
                        target_id=target.id,
                        ig_post_id=download_id,
                        ig_shortcode=download_id,
                        source_url=f"https://instagram.com/p/{download_id}",
                        local_path=f"./sample_videos/sample{j+1}.mp4",
                        permission_proof_path=f"./sample_proofs/proof_{download_id}.txt",
                        file_size=1024 * 1024 * (5 + j),  # 5-6 MB
                        duration_seconds=30 + j * 10,
                        caption=f"Demo video {j+1} from @{target.username} - This is a sample caption for testing purposes! #demo #test #viral"
                    )
                    session.add(download)
                    session.commit()
                    print(f"  ✅ Created download: {download_id}")


def create_demo_transforms():
    """Create demo transform records."""
    print("🎬 Creating demo transforms...")
    
    with get_db_session() as session:
        downloads = session.query(Download).all()
        
        for download in downloads:
            # Check if transform already exists
            existing = session.query(Transform).filter_by(
                download_id=download.id
            ).first()
            
            if not existing:
                transform = Transform(
                    download_id=download.id,
                    input_path=download.local_path,
                    output_path=f"./storage/transforms/transform_{download.id}.mp4",
                    thumbnail_path=f"./storage/thumbnails/thumb_{download.id}.jpg",
                    phash=f"demo_hash_{download.id}_{hash(download.ig_post_id) % 10000}",
                    status=StatusEnum.COMPLETED,
                    transform_duration_seconds=35
                )
                session.add(transform)
                session.commit()
                print(f"  ✅ Created transform for download {download.id}")


def create_demo_uploads():
    """Create demo upload records."""
    print("📤 Creating demo uploads...")
    
    with get_db_session() as session:
        transforms = session.query(Transform).all()
        
        for i, transform in enumerate(transforms):
            # Check if upload already exists
            existing = session.query(Upload).filter_by(
                transform_id=transform.id
            ).first()
            
            if not existing:
                status = StatusEnum.COMPLETED if i < 2 else StatusEnum.PENDING
                yt_video_id = f"demo_yt_{transform.id}" if status == StatusEnum.COMPLETED else None
                
                upload = Upload(
                    transform_id=transform.id,
                    yt_video_id=yt_video_id,
                    title=f"Demo Video from @{transform.download.target.username} - Amazing Content!",
                    description=f"""🎬 Original Creator: @{transform.download.target.username}
🔗 Original Post: {transform.download.source_url}

📄 Permission Proof:
Content downloaded from public Instagram account with permission.
Proof stored at: {transform.download.permission_proof_path}

📝 About this video:
This content was shared from a public Instagram account and is
available for public viewing. All credits go to the original creator.

🎯 Follow for more viral content!
👍 Like if you enjoyed this video!
🔔 Subscribe for daily uploads!

#Shorts #Viral #Instagram #Trending #Content""",
                    tags="demo,viral,shorts,instagram,trending,content",
                    status=status,
                    uploaded_at=datetime.utcnow() - timedelta(hours=1) if status == StatusEnum.COMPLETED else None
                )
                session.add(upload)
                session.commit()
                print(f"  ✅ Created upload for transform {transform.id} (status: {status})")


def create_demo_approvals():
    """Create demo approval records."""
    print("✅ Creating demo approvals...")
    
    with get_db_session() as session:
        uploads = session.query(Upload).all()
        
        for upload in uploads:
            # Check if approval already exists
            existing = session.query(Approval).filter_by(
                upload_id=upload.id
            ).first()
            
            if not existing:
                status = StatusEnum.COMPLETED if upload.status == StatusEnum.COMPLETED else StatusEnum.PENDING
                
                approval = Approval(
                    upload_id=upload.id,
                    telegram_message_id=12345 + upload.id,
                    status=status,
                    approved_by="demo_admin" if status == StatusEnum.COMPLETED else None,
                    approved_at=datetime.utcnow() - timedelta(hours=1) if status == StatusEnum.COMPLETED else None
                )
                session.add(approval)
                session.commit()
                print(f"  ✅ Created approval for upload {upload.id} (status: {status})")


def create_demo_permissions():
    """Create demo permission records."""
    print("📄 Creating demo permissions...")
    
    with get_db_session() as session:
        downloads = session.query(Download).all()
        
        for download in downloads:
            # Check if permission already exists
            existing = session.query(Permission).filter_by(
                download_id=download.id
            ).first()
            
            if not existing:
                permission = Permission(
                    download_id=download.id,
                    proof_type="file",
                    proof_path=download.permission_proof_path,
                    description=f"Demo permission proof for @{download.target.username}",
                    proof_content=b"Demo permission proof content for testing purposes."
                )
                session.add(permission)
                session.commit()
                print(f"  ✅ Created permission for download {download.id}")


def create_demo_logs():
    """Create demo log entries."""
    print("📝 Creating demo logs...")
    
    demo_logs = [
        {"level": "INFO", "module": "ig_downloader", "message": "Downloaded video from @demo_creator1"},
        {"level": "INFO", "module": "transform", "message": "Transformed video to YouTube Shorts format"},
        {"level": "INFO", "module": "youtube_client", "message": "Uploaded video to YouTube successfully"},
        {"level": "WARNING", "module": "scheduler", "message": "Scheduled job completed with warnings"},
        {"level": "ERROR", "module": "ig_downloader", "message": "Failed to download from @demo_creator3"},
    ]
    
    with get_db_session() as session:
        for log_data in demo_logs:
            log = LogEntry(
                level=log_data["level"],
                module=log_data["module"],
                message=log_data["message"],
                details=json.dumps({"demo": True, "timestamp": datetime.utcnow().isoformat()})
            )
            session.add(log)
            session.commit()
            print(f"  ✅ Created log: {log_data['level']} - {log_data['message']}")


def create_demo_system_status():
    """Create demo system status."""
    print("⚙️  Creating demo system status...")
    
    with get_db_session() as session:
        # Check if system status already exists
        existing = session.query(SystemStatus).first()
        
        if not existing:
            status = SystemStatus(
                scheduler_running=True,
                last_run=datetime.utcnow() - timedelta(hours=1),
                next_run=datetime.utcnow() + timedelta(hours=3),
                total_downloads=4,
                total_uploads=2,
                last_error=None,
                last_error_at=None
            )
            session.add(status)
            session.commit()
            print("  ✅ Created system status record")
        else:
            print("  ⚠️  System status already exists")


def main():
    """Main function to create demo database."""
    print("🎬 YouTube Auto Upload - Demo Database Creator")
    print("=" * 50)
    
    try:
        # Initialize database
        print("🗄️  Initializing database...")
        init_database()
        print("  ✅ Database initialized")
        
        # Create demo data
        create_demo_targets()
        create_demo_downloads()
        create_demo_transforms()
        create_demo_uploads()
        create_demo_approvals()
        create_demo_permissions()
        create_demo_logs()
        create_demo_system_status()
        
        print("\n🎉 Demo database created successfully!")
        print("\nDemo data includes:")
        print("• 3 Instagram targets (2 active, 1 inactive)")
        print("• 4 download records")
        print("• 4 transform records")
        print("• 4 upload records (2 completed, 2 pending)")
        print("• 4 approval records")
        print("• 4 permission records")
        print("• 5 log entries")
        print("• 1 system status record")
        
        print("\nTo test the demo:")
        print("1. Set DEMO_MODE=true in your .env file")
        print("2. Run: python -m app.main")
        print("3. Check the API endpoints at http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ Error creating demo database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
