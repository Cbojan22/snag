"""Filesystem Utilities — File and path helpers.

Provides helpers for creating download directories, generating
safe filenames, and managing the download output structure.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

# Default download directory
DEFAULT_DOWNLOAD_DIR = Path.home() / "Desktop" / "Snag"


def ensure_download_dir(path: Path | None = None) -> Path:
    """Ensure the download directory exists, creating if needed.

    Args:
        path: Custom download directory. Uses default if None.

    Returns:
        Path to the download directory.
    """
    download_dir = path or DEFAULT_DOWNLOAD_DIR
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def safe_filename(name: str, max_length: int = 200) -> str:
    """Convert a string to a safe filename.

    Removes or replaces characters that are invalid in filenames
    across different operating systems.

    Args:
        name: The original filename.
        max_length: Maximum filename length.

    Returns:
        Sanitized filename string.
    """
    # Normalize unicode characters
    name = unicodedata.normalize("NFKD", name)

    # Remove or replace unsafe characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)

    # Remove leading/trailing dots and spaces
    name = name.strip(". ")

    # Collapse multiple underscores/spaces
    name = re.sub(r"[_\s]+", "_", name)

    # Truncate to max length
    if len(name) > max_length:
        name = name[:max_length].rstrip("_")

    return name or "download"


def get_unique_filepath(filepath: Path) -> Path:
    """Get a unique filepath by appending a number if file exists.

    Args:
        filepath: Desired file path.

    Returns:
        Unique path (may have number appended to stem).
    """
    if not filepath.exists():
        return filepath

    stem = filepath.stem
    suffix = filepath.suffix
    parent = filepath.parent
    counter = 1

    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def format_filesize(size_bytes: int | float) -> str:
    """Format file size in bytes to human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string like "1.5 MB".
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: int | float) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string like "1:23:45" or "3:45".
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
