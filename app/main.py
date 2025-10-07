"""
Main FastAPI application for YouTube Auto Upload.

This module orchestrates all components:
- FastAPI web server with health endpoints
- Telegram bot for admin control
- Scheduler for automated processing
- Background workers for pipeline execution
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .config import get_settings
from .db import init_database, get_database_info, get_system_status
from .models import StatusEnum
from .scheduler import get_scheduler_status, run_pipeline_now
from .telegram_bot import create_telegram_bot
from .workers import process_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global components
telegram_bot = None
scheduler_task = None
bot_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global telegram_bot, scheduler_task, bot_task
    
    settings = get_settings()
    
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    # Validate configuration
    if settings.is_production_mode():
        errors = settings.validate_production_config()
        if errors:
            logger.error(f"Configuration errors: {errors}")
            # Don't fail in demo mode, but log errors
    
    # Start Telegram bot (if not in demo mode)
    if not settings.is_demo_mode() and settings.telegram_bot_token:
        telegram_bot = create_telegram_bot()
        
        # Start bot in background
        bot_task = asyncio.create_task(telegram_bot.start_bot())
        logger.info("Telegram bot started")
    
    # Start scheduler
    from .scheduler import start_scheduler
    await start_scheduler()
    logger.info("Scheduler started")
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    
    # Stop scheduler
    from .scheduler import stop_scheduler
    await stop_scheduler()
    logger.info("Scheduler stopped")
    
    # Stop Telegram bot
    if telegram_bot and bot_task:
        await telegram_bot.stop_bot()
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        logger.info("Telegram bot stopped")
    
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="YouTube Auto Upload API",
    description="Automated pipeline for downloading Instagram videos and uploading to YouTube",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


@app.get("/status")
async def get_status():
    """Get comprehensive system status."""
    try:
        # Get database info
        db_info = get_database_info()
        
        # Get scheduler status
        scheduler_info = get_scheduler_status()
        
        # Get system status
        system_info = get_system_status()
        
        # Get settings info
        settings = get_settings()
        
        return {
            "database": db_info,
            "scheduler": scheduler_info,
            "system": system_info,
            "settings": {
                "demo_mode": settings.is_demo_mode(),
                "timezone": settings.timezone,
                "schedule_times": settings.schedule_times,
                "storage_path": settings.storage_path,
                "db_url": settings.db_url
            },
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/run-pipeline")
async def run_pipeline_manual():
    """Manually trigger the video processing pipeline."""
    try:
        logger.info("Manual pipeline run triggered")
        
        # Run pipeline in background
        asyncio.create_task(process_pipeline())
        
        return {"message": "Pipeline started", "status": "running"}
        
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/approve/{upload_id}")
async def approve_upload(upload_id: int):
    """Approve an upload (internal API endpoint)."""
    try:
        from .db import get_db_session
        from .models import Approval, StatusEnum
        
        with get_db_session() as session:
            approval = session.query(Approval).filter_by(upload_id=upload_id).first()
            if not approval:
                raise HTTPException(status_code=404, detail="Approval not found")
            
            approval.status = StatusEnum.COMPLETED
            approval.approved_at = datetime.utcnow()
            session.commit()
        
        return {"message": "Upload approved", "upload_id": upload_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/reject/{upload_id}")
async def reject_upload(upload_id: int):
    """Reject an upload (internal API endpoint)."""
    try:
        from .db import get_db_session
        from .models import Approval, StatusEnum
        
        with get_db_session() as session:
            approval = session.query(Approval).filter_by(upload_id=upload_id).first()
            if not approval:
                raise HTTPException(status_code=404, detail="Approval not found")
            
            approval.status = StatusEnum.REJECTED
            approval.approved_at = datetime.utcnow()
            session.commit()
        
        return {"message": "Upload rejected", "upload_id": upload_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_statistics():
    """Get detailed statistics."""
    try:
        from .db import get_db_session
        from .models import (
            InstagramTarget, Download, Transform, Upload, 
            Approval, Permission, LogEntry
        )
        
        with get_db_session() as session:
            stats = {
                "targets": {
                    "total": session.query(InstagramTarget).count(),
                    "active": session.query(InstagramTarget).filter_by(is_active=True).count(),
                    "inactive": session.query(InstagramTarget).filter_by(is_active=False).count()
                },
                "downloads": {
                    "total": session.query(Download).count()
                },
                "transforms": {
                    "total": session.query(Transform).count(),
                    "completed": session.query(Transform).filter_by(status=StatusEnum.COMPLETED).count(),
                    "failed": session.query(Transform).filter_by(status=StatusEnum.FAILED).count(),
                    "duplicates": session.query(Transform).filter_by(status=StatusEnum.DUPLICATE).count()
                },
                "uploads": {
                    "total": session.query(Upload).count(),
                    "completed": session.query(Upload).filter_by(status=StatusEnum.COMPLETED).count(),
                    "failed": session.query(Upload).filter_by(status=StatusEnum.FAILED).count(),
                    "pending": session.query(Upload).filter_by(status=StatusEnum.PENDING).count()
                },
                "approvals": {
                    "total": session.query(Approval).count(),
                    "pending": session.query(Approval).filter_by(status=StatusEnum.PENDING).count(),
                    "completed": session.query(Approval).filter_by(status=StatusEnum.COMPLETED).count(),
                    "rejected": session.query(Approval).filter_by(status=StatusEnum.REJECTED).count()
                },
                "permissions": {
                    "total": session.query(Permission).count()
                },
                "logs": {
                    "total": session.query(LogEntry).count()
                }
            }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with basic information."""
    settings = get_settings()
    
    return {
        "message": "YouTube Auto Upload API",
        "version": "1.0.0",
        "mode": "demo" if settings.is_demo_mode() else "production",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "stats": "/stats",
            "docs": "/docs",
            "admin": {
                "run_pipeline": "/admin/run-pipeline",
                "approve": "/admin/approve/{upload_id}",
                "reject": "/admin/reject/{upload_id}"
            }
        }
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_demo_mode(),
        log_level=settings.log_level.lower()
    )
