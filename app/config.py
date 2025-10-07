"""
Configuration management using Pydantic settings.

This module handles all environment variable loading and validation
for the YouTube Auto Upload application.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    # Demo Mode Configuration
    demo_mode: bool = Field(default=True)
    
    # Timezone and Scheduling
    timezone: str = Field(default="Asia/Karachi")
    schedule_times: List[str] = Field(default=["08:00", "12:00", "16:00"])
    
    # YouTube API Configuration
    youtube_client_secrets: str = Field(default="./client_secrets.json")
    token_file: str = Field(default="./token.json")
    
    # Telegram Bot Configuration
    telegram_bot_token: str = Field(default="")
    telegram_admin_id: int = Field(default=0)
    
    # Storage and Database
    storage_path: str = Field(default="./storage")
    db_url: str = Field(default="sqlite:///./data/app.db")
    
    # Branded Assets
    branded_intro: str = Field(default="./assets/intro.mp4")
    branded_outro: str = Field(default="./assets/outro.mp4")
    
    # Channel Configuration
    channel_title: str = Field(default="My YouTube Channel")
    
    # Logging
    log_level: str = Field(default="INFO")
    
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
    
    @field_validator('schedule_times', mode='before')
    @classmethod
    def parse_schedule_times(cls, v):
        """Parse comma-separated schedule times."""
        if isinstance(v, str):
            return [time.strip() for time in v.split(',')]
        return v
    
    @field_validator('demo_mode', mode='before')
    @classmethod
    def parse_demo_mode(cls, v):
        """Parse demo mode boolean."""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    @field_validator('telegram_admin_id', mode='before')
    @classmethod
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
    import os
    # Load from environment variables
    env_vars = {
        'demo_mode': os.getenv('DEMO_MODE', 'true').lower() in ('true', '1', 'yes', 'on'),
        'timezone': os.getenv('TIMEZONE', 'Asia/Karachi'),
        'schedule_times': [t.strip() for t in os.getenv('SCHEDULE_TIMES', '08:00,12:00,16:00').split(',')],
        'youtube_client_secrets': os.getenv('YOUTUBE_CLIENT_SECRETS', './client_secrets.json'),
        'token_file': os.getenv('TOKEN_FILE', './token.json'),
        'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'telegram_admin_id': int(os.getenv('TELEGRAM_ADMIN_ID', '0')) if os.getenv('TELEGRAM_ADMIN_ID', '0').isdigit() else 0,
        'storage_path': os.getenv('STORAGE_PATH', './storage'),
        'db_url': os.getenv('DB_URL', 'sqlite:///./data/app.db'),
        'branded_intro': os.getenv('BRANDED_INTRO', './assets/intro.mp4'),
        'branded_outro': os.getenv('BRANDED_OUTRO', './assets/outro.mp4'),
        'channel_title': os.getenv('CHANNEL_TITLE', 'My YouTube Channel'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    }
    settings = Settings(
        demo_mode=bool(env_vars['demo_mode']),
        timezone=str(env_vars['timezone']),
        schedule_times=env_vars['schedule_times'],  # type: ignore
        youtube_client_secrets=str(env_vars['youtube_client_secrets']),
        token_file=str(env_vars['token_file']),
        telegram_bot_token=str(env_vars['telegram_bot_token']),
        telegram_admin_id=env_vars['telegram_admin_id'],  # type: ignore
        storage_path=str(env_vars['storage_path']),
        db_url=str(env_vars['db_url']),
        branded_intro=str(env_vars['branded_intro']),
        branded_outro=str(env_vars['branded_outro']),
        channel_title=str(env_vars['channel_title']),
        log_level=str(env_vars['log_level'])
    )
    return settings
