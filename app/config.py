"""
Configuration management using Pydantic settings.

This module handles all environment variable loading and validation
for the YouTube Auto Upload application.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Demo Mode Configuration
    demo_mode: bool = Field(default=True, env="DEMO_MODE")
    
    # Timezone and Scheduling
    timezone: str = Field(default="Asia/Karachi", env="TIMEZONE")
    schedule_times: List[str] = Field(default=["08:00", "12:00", "16:00"], env="SCHEDULE_TIMES")
    
    # YouTube API Configuration
    youtube_client_secrets: str = Field(default="./client_secrets.json", env="YOUTUBE_CLIENT_SECRETS")
    token_file: str = Field(default="./token.json", env="TOKEN_FILE")
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    telegram_admin_id: int = Field(default=0, env="TELEGRAM_ADMIN_ID")
    
    # Storage and Database
    storage_path: str = Field(default="./storage", env="STORAGE_PATH")
    db_url: str = Field(default="sqlite:///./data/app.db", env="DB_URL")
    
    # Branded Assets
    branded_intro: str = Field(default="./assets/intro.mp4", env="BRANDED_INTRO")
    branded_outro: str = Field(default="./assets/outro.mp4", env="BRANDED_OUTRO")
    
    # Channel Configuration
    channel_title: str = Field(default="My YouTube Channel", env="CHANNEL_TITLE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Video Processing Settings
    target_resolution: tuple = (1080, 1920)  # 9:16 aspect ratio
    phash_threshold: int = 10  # Hamming distance threshold for deduplication
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    # Instagram Settings
    max_posts_per_account: int = 5  # Max posts to fetch per account per run
    download_timeout: int = 300  # 5 minutes timeout for downloads
    
    # YouTube Settings
    youtube_upload_chunk_size: int = 1024 * 1024  # 1MB chunks
    youtube_max_retry_attempts: int = 3
    
    @validator('schedule_times', pre=True)
    def parse_schedule_times(cls, v):
        """Parse comma-separated schedule times."""
        if isinstance(v, str):
            return [time.strip() for time in v.split(',')]
        return v
    
    @validator('demo_mode', pre=True)
    def parse_demo_mode(cls, v):
        """Parse demo mode boolean."""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    @validator('telegram_admin_id', pre=True)
    def parse_telegram_admin_id(cls, v):
        """Parse telegram admin ID."""
        if isinstance(v, str):
            return int(v) if v.isdigit() else 0
        return v
    
    @property
    def storage_path_obj(self) -> Path:
        """Get storage path as Path object."""
        return Path(self.storage_path)
    
    @property
    def data_path_obj(self) -> Path:
        """Get data directory path as Path object."""
        return Path("data")
    
    @property
    def assets_path_obj(self) -> Path:
        """Get assets directory path as Path object."""
        return Path("assets")
    
    @property
    def sample_videos_path_obj(self) -> Path:
        """Get sample videos directory path as Path object."""
        return Path("sample_videos")
    
    @property
    def sample_proofs_path_obj(self) -> Path:
        """Get sample proofs directory path as Path object."""
        return Path("sample_proofs")
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.storage_path_obj,
            self.data_path_obj,
            self.assets_path_obj,
            self.sample_videos_path_obj,
            self.sample_proofs_path_obj,
            self.storage_path_obj / "downloads",
            self.storage_path_obj / "transforms",
            self.storage_path_obj / "thumbnails",
            self.storage_path_obj / "proofs",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.demo_mode
    
    def is_production_mode(self) -> bool:
        """Check if running in production mode."""
        return not self.demo_mode
    
    def validate_production_config(self) -> List[str]:
        """Validate configuration for production mode."""
        errors = []
        
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required for production mode")
        
        if not self.telegram_admin_id:
            errors.append("TELEGRAM_ADMIN_ID is required for production mode")
        
        if not Path(self.youtube_client_secrets).exists():
            errors.append(f"YouTube client secrets file not found: {self.youtube_client_secrets}")
        
        if not Path(self.token_file).exists():
            errors.append(f"YouTube token file not found: {self.token_file}")
        
        return errors
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global settings
    settings = Settings()
    return settings
