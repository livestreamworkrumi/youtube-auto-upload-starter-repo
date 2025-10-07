"""
Database connection and session management.

This module provides database engine, session management, and utility functions
for the YouTube Auto Upload application.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base, create_tables

logger = logging.getLogger(__name__)

# Global database engine and session maker
_engine: Optional[Engine] = None
_session_maker: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """Get the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.db_url,
            echo=settings.log_level == "DEBUG",
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Enable foreign key constraints for SQLite
        if settings.db_url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    
    return _engine


def get_session_maker() -> sessionmaker:
    """Get the SQLAlchemy session maker."""
    global _session_maker
    if _session_maker is None:
        engine = get_engine()
        _session_maker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _session_maker


def init_database() -> None:
    """Initialize the database by creating all tables."""
    try:
        engine = get_engine()
        create_tables(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_session() -> Session:
    """Get a new database session."""
    session_maker = get_session_maker()
    return session_maker()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def close_connections() -> None:
    """Close all database connections."""
    global _engine, _session_maker
    if _engine:
        _engine.dispose()
        _engine = None
    _session_maker = None


def reset_database() -> None:
    """Reset the database by dropping and recreating all tables."""
    try:
        engine = get_engine()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Database reset successfully")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        raise


def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """Get database information and statistics."""
    try:
        with get_db_session() as session:
            from .models import (
                InstagramTarget, Download, Transform, Upload, 
                Approval, Permission, LogEntry, SystemStatus
            )
            
            info = {
                "connection_status": "connected",
                "tables": {
                    "instagram_targets": session.query(InstagramTarget).count(),
                    "downloads": session.query(Download).count(),
                    "transforms": session.query(Transform).count(),
                    "uploads": session.query(Upload).count(),
                    "approvals": session.query(Approval).count(),
                    "permissions": session.query(Permission).count(),
                    "logs": session.query(LogEntry).count(),
                    "system_status": session.query(SystemStatus).count(),
                }
            }
            return info
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "connection_status": "error",
            "error": str(e),
            "tables": {}
        }


# Database utility functions for common operations
def log_entry(level: str, module: str, message: str, details: Optional[str] = None) -> None:
    """Log an entry to the database."""
    try:
        with get_db_session() as session:
            from .models import LogEntry
            log = LogEntry(
                level=level,
                module=module,
                message=message,
                details=details
            )
            session.add(log)
            session.commit()
    except Exception as e:
        logger.error(f"Failed to log entry to database: {e}")


def update_system_status(**kwargs) -> None:
    """Update system status record."""
    try:
        with get_db_session() as session:
            from .models import SystemStatus
            from datetime import datetime
            
            status = session.query(SystemStatus).first()
            if not status:
                status = SystemStatus()
                session.add(status)
            
            for key, value in kwargs.items():
                if hasattr(status, key):
                    setattr(status, key, value)
            
            # status.updated_at = datetime.utcnow()  # This will be handled by the trigger
            session.commit()
    except Exception as e:
        logger.error(f"Failed to update system status: {e}")


def get_system_status() -> dict:
    """Get current system status."""
    try:
        with get_db_session() as session:
            from .models import SystemStatus
            status = session.query(SystemStatus).first()
            if status:
                return {
                    "scheduler_running": status.scheduler_running,
                    "last_run": status.last_run,
                    "next_run": status.next_run,
                    "total_downloads": status.total_downloads,
                    "total_uploads": status.total_uploads,
                    "last_error": status.last_error,
                    "last_error_at": status.last_error_at,
                    "updated_at": status.updated_at,
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return {}


# Initialize database when module is imported
def init() -> None:
    """Initialize database module."""
    settings = get_settings()
    settings.ensure_directories()
    init_database()


if __name__ == "__main__":
    # Allow running this module directly to initialize database
    init()
    print("Database initialized successfully")
