"""
SQLAlchemy database models for the YouTube Auto Upload application.

This module defines all database tables and their relationships for tracking
Instagram downloads, video transformations, YouTube uploads, and system logs.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer,
    LargeBinary, String, Text, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class StatusEnum(str, Enum):
    """Status enumeration for various operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class InstagramTarget(Base):
    """Instagram accounts to monitor for new posts."""
    
    __tablename__ = "instagram_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_checked = Column(DateTime, default=None)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    downloads = relationship("Download", back_populates="target")


class Download(Base):
    """Downloaded Instagram posts."""
    
    __tablename__ = "downloads"
    
    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("instagram_targets.id"), nullable=False)
    ig_post_id = Column(String(255), unique=True, index=True, nullable=False)
    ig_shortcode = Column(String(255), index=True, nullable=False)
    source_url = Column(Text, nullable=False)
    local_path = Column(String(500), nullable=False)
    permission_proof_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    caption = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    target = relationship("InstagramTarget", back_populates="downloads")
    transforms = relationship("Transform", back_populates="download")


class Transform(Base):
    """Video transformation records."""
    
    __tablename__ = "transforms"
    
    id = Column(Integer, primary_key=True, index=True)
    download_id = Column(Integer, ForeignKey("downloads.id"), nullable=False)
    input_path = Column(String(500), nullable=False)
    output_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    phash = Column(String(255), index=True, nullable=True)
    status = Column(SQLEnum(StatusEnum), default=StatusEnum.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    transform_duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    download = relationship("Download", back_populates="transforms")
    uploads = relationship("Upload", back_populates="transform")


class Upload(Base):
    """YouTube upload records."""
    
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    transform_id = Column(Integer, ForeignKey("transforms.id"), nullable=False)
    yt_video_id = Column(String(255), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(Text, nullable=True)  # JSON string of tags
    status = Column(SQLEnum(StatusEnum), default=StatusEnum.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    transform = relationship("Transform", back_populates="uploads")
    approvals = relationship("Approval", back_populates="upload")


class Approval(Base):
    """Admin approval records for uploads."""
    
    __tablename__ = "approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    telegram_message_id = Column(Integer, nullable=True)
    status = Column(SQLEnum(StatusEnum), default=StatusEnum.PENDING, nullable=False)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    upload = relationship("Upload", back_populates="approvals")


class Permission(Base):
    """Permission proof artifacts."""
    
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    download_id = Column(Integer, ForeignKey("downloads.id"), nullable=False)
    proof_type = Column(String(100), nullable=False)  # 'file', 'url', 'screenshot'
    proof_path = Column(String(500), nullable=False)
    proof_content = Column(LargeBinary, nullable=True)  # For storing file content
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    download = relationship("Download")


class LogEntry(Base):
    """Application logs."""
    
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False, index=True)
    module = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON string for additional details
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)


class SystemStatus(Base):
    """System status and configuration tracking."""
    
    __tablename__ = "system_status"
    
    id = Column(Integer, primary_key=True, index=True)
    scheduler_running = Column(Boolean, default=False, nullable=False)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    total_downloads = Column(Integer, default=0, nullable=False)
    total_uploads = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


# Database utility functions
def create_tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_session_maker(engine):
    """Get SQLAlchemy session maker."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
