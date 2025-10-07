"""
Timezone-aware scheduler for automated video processing.

This module handles:
- Scheduled downloads from Instagram targets
- Timezone-aware scheduling for Pakistan times
- Job queuing and execution
- System status tracking
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

try:
    import pytz
except ImportError:
    pytz = None  # type: ignore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import get_settings
from .db import get_db_session, update_system_status
from .ig_downloader import InstagramDownloader
from .workers import process_pipeline

logger = logging.getLogger(__name__)


class VideoScheduler:
    """Timezone-aware scheduler for video processing pipeline."""
    
    def __init__(self):
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler(timezone=self.settings.timezone)
        self.is_running = False
        
        # Parse schedule times
        self.schedule_times = self._parse_schedule_times()
        
        # Timezone setup
        if pytz:
            self.timezone = pytz.timezone(self.settings.timezone)
        else:
            from zoneinfo import ZoneInfo
            self.timezone = ZoneInfo(self.settings.timezone)
    
    def _parse_schedule_times(self) -> List[str]:
        """Parse schedule times from configuration."""
        return self.settings.schedule_times
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.settings.is_demo_mode()
    
    async def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Add scheduled jobs for each time
            for schedule_time in self.schedule_times:
                hour, minute = map(int, schedule_time.split(':'))
                
                # Add cron job for each scheduled time
                self.scheduler.add_job(
                    func=self._run_pipeline,
                    trigger=CronTrigger(
                        hour=hour,
                        minute=minute,
                        timezone=self.timezone
                    ),
                    id=f"video_pipeline_{hour}_{minute}",
                    name=f"Video Pipeline at {schedule_time}",
                    replace_existing=True,
                    max_instances=1
                )
                
                logger.info(f"Scheduled job for {schedule_time} {self.settings.timezone}")
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            # Update system status
            update_system_status(
                scheduler_running=True,
                next_run=self._get_next_run_time()
            )
            
            logger.info("Video scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            
            # Update system status
            update_system_status(
                scheduler_running=False,
                next_run=None
            )
            
            logger.info("Video scheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            raise
    
    async def _run_pipeline(self):
        """Run the complete video processing pipeline."""
        try:
            logger.info("Starting scheduled video processing pipeline")
            
            # Update last run time
            update_system_status(last_run=datetime.utcnow())
            
            # Run the pipeline
            await process_pipeline()
            
            # Update next run time
            update_system_status(next_run=self._get_next_run_time())
            
            logger.info("Scheduled video processing pipeline completed")
            
        except Exception as e:
            logger.error(f"Scheduled pipeline failed: {e}")
            
            # Update system status with error
            update_system_status(
                last_error=str(e),
                last_error_at=datetime.utcnow()
            )
            
            # Send error notification if not in demo mode
            if not self.is_demo_mode():
                from .telegram_bot import create_telegram_bot
                bot = create_telegram_bot()
                await bot.send_error_notification(
                    str(e),
                    "Scheduled pipeline execution"
                )
    
    def _get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time."""
        if not self.is_running or not self.schedule_times:
            return None
        
        now = datetime.now(self.timezone)
        next_run = None
        
        for schedule_time in self.schedule_times:
            hour, minute = map(int, schedule_time.split(':'))
            
            # Create datetime for today at this time
            today_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if today_run <= now:
                today_run += timedelta(days=1)
            
            # Update next_run if this is earlier
            if next_run is None or today_run < next_run:
                next_run = today_run
        
        if next_run is None:
            return None
        if pytz:
            return next_run.astimezone(pytz.UTC)
        else:
            from zoneinfo import ZoneInfo
            return next_run.astimezone(ZoneInfo('UTC'))
    
    def get_status(self) -> dict:
        """Get scheduler status information."""
        jobs = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
        
        return {
            "running": self.is_running,
            "timezone": self.settings.timezone,
            "schedule_times": self.schedule_times,
            "jobs": jobs,
            "next_run": (self._get_next_run_time().isoformat() if self._get_next_run_time() is not None else None),
            "demo_mode": self.is_demo_mode()
        }
    
    async def run_now(self):
        """Run the pipeline immediately (for testing)."""
        logger.info("Running pipeline immediately (manual trigger)")
        await self._run_pipeline()
    
    async def add_schedule_time(self, time_str: str):
        """Add a new schedule time."""
        try:
            hour, minute = map(int, time_str.split(':'))
            
            # Validate time
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError(f"Invalid time format: {time_str}")
            
            # Add to schedule times if not already present
            if time_str not in self.schedule_times:
                self.schedule_times.append(time_str)
                
                # Add cron job
                self.scheduler.add_job(
                    func=self._run_pipeline,
                    trigger=CronTrigger(
                        hour=hour,
                        minute=minute,
                        timezone=self.timezone
                    ),
                    id=f"video_pipeline_{hour}_{minute}",
                    name=f"Video Pipeline at {time_str}",
                    replace_existing=True,
                    max_instances=1
                )
                
                logger.info(f"Added schedule time: {time_str}")
                
        except Exception as e:
            logger.error(f"Failed to add schedule time {time_str}: {e}")
            raise
    
    async def remove_schedule_time(self, time_str: str):
        """Remove a schedule time."""
        try:
            if time_str in self.schedule_times:
                self.schedule_times.remove(time_str)
                
                # Remove job
                hour, minute = map(int, time_str.split(':'))
                job_id = f"video_pipeline_{hour}_{minute}"
                
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                
                logger.info(f"Removed schedule time: {time_str}")
            else:
                logger.warning(f"Schedule time {time_str} not found")
                
        except Exception as e:
            logger.error(f"Failed to remove schedule time {time_str}: {e}")
            raise


def create_scheduler() -> VideoScheduler:
    """Create and return a video scheduler instance."""
    return VideoScheduler()


# Global scheduler instance
_scheduler = None


def get_scheduler() -> VideoScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    return _scheduler


async def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()


async def run_pipeline_now():
    """Run the pipeline immediately."""
    scheduler = get_scheduler()
    await scheduler.run_now()


def get_scheduler_status() -> dict:
    """Get scheduler status."""
    scheduler = get_scheduler()
    return scheduler.get_status()


if __name__ == "__main__":
    # Allow running this module directly for testing
    import asyncio
    
    async def test_scheduler():
        scheduler = create_scheduler()
        
        print(f"Scheduler status: {scheduler.get_status()}")
        
        if not scheduler.is_demo_mode():
            await scheduler.start()
            print("Scheduler started")
            
            # Wait a bit
            await asyncio.sleep(5)
            
            await scheduler.stop()
            print("Scheduler stopped")
        else:
            print("Demo mode: scheduler test completed")
    
    asyncio.run(test_scheduler())
