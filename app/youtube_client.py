"""
Utility functions for the YouTube Auto Upload application.

This module provides helper functions for:
- SEO title and description generation
- Thumbnail generation
- File operations
- Text processing
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import List, Optional

from PIL import Image

from .config import get_settings
from .models import Download, Transform

logger = logging.getLogger(__name__)


def generate_seo_title(download: Download) -> str:
    """Generate SEO-optimized title for YouTube video.
    
    Args:
        download: Download record with metadata
        
    Returns:
        SEO-optimized title
    """
    try:
        # Base title components
        username = download.target.username
        base_title = f"@{username}"
        
        # Extract keywords from caption if available
        keywords: List[str] = []
        if download.caption:
            # Clean and extract potential keywords
            clean_caption = re.sub(r'[^\w\s]', ' ', download.caption.lower())
            words = clean_caption.split()
            
            # Filter for meaningful words (length > 3, not common words)
            common_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were'}
            
            for word in words:
                if len(word) > 3 and word not in common_words and len(keywords) < 5:
                    keywords.append(word.title())
        
        # Build title
        if keywords:
            title = f"{base_title} - {' '.join(keywords[:3])}"
        else:
            title = f"{base_title} - Amazing Content"
        
        # Ensure title is not too long (YouTube limit is 100 chars)
        if len(title) > 90:
            title = title[:87] + "..."
        
        return title
        
    except Exception as e:
        logger.error(f"Error generating SEO title: {e}")
        return f"@{download.target.username} - Viral Content"


def generate_seo_description(download: Download, transform: Transform) -> str:
    """Generate SEO-optimized description for YouTube video.
    
    Args:
        download: Download record with metadata
        transform: Transform record with video info
        
    Returns:
        SEO-optimized description
    """
    try:
        username = download.target.username
        original_url = download.source_url
        proof_path = download.permission_proof_path
        
        # Base description
        description_parts = [
            f"🎬 Original Creator: @{username}",
            f"🔗 Original Post: {original_url}",
            "",
            "📄 Permission Proof:",
            f"Content downloaded from public Instagram account with permission.",
            f"Proof stored at: {proof_path}",
            "",
            "📝 About this video:",
            "This content was shared from a public Instagram account and is",
            "available for public viewing. All credits go to the original creator.",
            "",
            "🎯 Follow for more viral content!",
            "👍 Like if you enjoyed this video!",
            "🔔 Subscribe for daily uploads!",
            "",
            "#Shorts #Viral #Instagram #Trending #Content"
        ]
        
        # Add original caption if available and not too long
        if download.caption and len(download.caption) < 200:
            description_parts.insert(-6, "")
            description_parts.insert(-6, f"📝 Original caption: {download.caption}")
        
        # Add channel branding
        settings = get_settings()
        description_parts.extend([
            "",
            f"📺 Channel: {settings.channel_title}",
            "🎬 Curated viral content from Instagram",
            "⚡ Daily uploads at 8AM, 12PM, 4PM (Pakistan time)"
        ])
        
        description = "\n".join(description_parts)
        
        # Ensure description is not too long (YouTube limit is 5000 chars)
        if len(description) > 4900:
            description = description[:4897] + "..."
        
        return description
        
    except Exception as e:
        logger.error(f"Error generating SEO description: {e}")
        return f"Original Creator: @{download.target.username}\nOriginal Post: {download.source_url}\n\nPermission granted from public Instagram account.\n\n#Shorts #Viral #Instagram"


def generate_thumbnail_from_video(video_path: str, output_path: str, timestamp: float = 1.0) -> bool:
    """Generate thumbnail from video at specified timestamp.
    
    Args:
        video_path: Path to input video file
        output_path: Path for output thumbnail
        timestamp: Time in seconds to extract frame
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from moviepy.editor import VideoFileClip
        
        with VideoFileClip(video_path) as video:
            # Ensure timestamp is within video duration
            if timestamp >= video.duration:
                timestamp = video.duration / 2
            
            # Save frame as image
            video.save_frame(output_path, t=timestamp)
            
            # Resize thumbnail to standard size
            with Image.open(output_path) as img:
                # Resize to 9:16 aspect ratio (480x854)
                img_resized = img.resize((480, 854), Image.Resampling.LANCZOS)
                img_resized.save(output_path, 'JPEG', quality=85)
            
            return True
            
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return False


def compute_file_hash(file_path: str) -> Optional[str]:
    """Compute MD5 hash of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 hash string or None if failed
    """
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    except Exception as e:
        logger.error(f"Error computing file hash: {e}")
        return None


def clean_filename(filename: str) -> str:
    """Clean filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove or replace invalid characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove extra spaces and dots
    cleaned = re.sub(r'\s+', '_', cleaned)
    cleaned = re.sub(r'\.+', '.', cleaned)
    
    # Ensure filename is not too long
    if len(cleaned) > 200:
        name, ext = Path(cleaned).stem, Path(cleaned).suffix
        cleaned = name[:200-len(ext)] + ext
    
    return cleaned


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float = size_float / 1024.0
        i += 1
    # Convert back to int for return formatting
    return f"{size_float:.1f} {size_names[i]}"


def format_duration(seconds: int) -> str:
    """Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours}h {minutes}m {remaining_seconds}s"


def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text.
    
    Args:
        text: Input text
        
    Returns:
        List of hashtags (without # symbol)
    """
    if not text:
        return []
    
    hashtag_pattern = r'#(\w+)'
    hashtags = re.findall(hashtag_pattern, text, re.IGNORECASE)
    
    return [tag.lower() for tag in hashtags]


def remove_hashtags(text: str) -> str:
    """Remove hashtags from text.
    
    Args:
        text: Input text
        
    Returns:
        Text without hashtags
    """
    if not text:
        return ""
    
    hashtag_pattern = r'#\w+\s*'
    return re.sub(hashtag_pattern, '', text).strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length.
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def is_valid_instagram_username(username: str) -> bool:
    """Validate Instagram username format.
    
    Args:
        username: Username to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not username:
        return False
    
    # Remove @ symbol if present
    username = username.replace('@', '')
    
    # Instagram username rules:
    # - 1-30 characters
    # - Only letters, numbers, periods, underscores
    # - Cannot start or end with period
    # - Cannot have consecutive periods
    if len(username) < 1 or len(username) > 30:
        return False
    
    if not re.match(r'^[a-zA-Z0-9._]+$', username):
        return False
    
    if username.startswith('.') or username.endswith('.'):
        return False
    
    if '..' in username:
        return False
    
    return True


def get_file_extension(filename: str) -> str:
    """Get file extension from filename.
    
    Args:
        filename: Filename
        
    Returns:
        File extension (without dot)
    """
    return Path(filename).suffix.lstrip('.').lower()


def ensure_directory(path: str) -> bool:
    """Ensure directory exists.
    
    Args:
        path: Directory path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return False


def get_video_info(video_path: str) -> dict:
    """Get basic video information.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dictionary with video info
    """
    try:
        from moviepy.editor import VideoFileClip
        
        with VideoFileClip(video_path) as video:
            return {
                "duration": video.duration,
                "fps": video.fps,
                "size": video.size,
                "has_audio": video.audio is not None
            }
            
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return {}


if __name__ == "__main__":
    # Test utility functions
    print("Testing utility functions...")
    
    # Test filename cleaning
    test_filename = "test file with spaces & symbols!.mp4"
    cleaned = clean_filename(test_filename)
    print(f"Cleaned filename: {cleaned}")
    
    # Test file size formatting
    test_size = 1024 * 1024 * 5  # 5MB
    formatted_size = format_file_size(test_size)
    print(f"Formatted size: {formatted_size}")
    
    # Test duration formatting
    test_duration = 3661  # 1h 1m 1s
    formatted_duration = format_duration(test_duration)
    print(f"Formatted duration: {formatted_duration}")
    
    # Test hashtag extraction
    test_text = "This is a #test with #multiple #hashtags and #more"
    hashtags = extract_hashtags(test_text)
    print(f"Extracted hashtags: {hashtags}")
    
    # Test Instagram username validation
    test_usernames = ["valid_username", "@valid_username", "invalid..username", "too_long_username_that_exceeds_limit"]
    for username in test_usernames:
        is_valid = is_valid_instagram_username(username)
        print(f"Username '{username}' is valid: {is_valid}")
    
    print("Utility function tests completed")
