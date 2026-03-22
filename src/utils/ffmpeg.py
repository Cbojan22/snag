"""FFmpeg Utilities — Detection and management of FFmpeg.

FFmpeg is required for merging separate video+audio streams
(common for YouTube 4K+, Reddit, etc.) and format conversion.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FFmpegInfo:
    """Information about the installed FFmpeg."""
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None


def detect_ffmpeg() -> FFmpegInfo:
    """Detect if FFmpeg is installed and get version info.

    Returns:
        FFmpegInfo with availability, path, and version.
    """
    ffmpeg_path = shutil.which("ffmpeg")

    if not ffmpeg_path:
        logger.warning("FFmpeg not found in PATH")
        return FFmpegInfo(available=False)

    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_line = result.stdout.split("\n")[0] if result.stdout else ""
        # Extract version number: "ffmpeg version 6.1.1 ..."
        parts = version_line.split()
        version = parts[2] if len(parts) >= 3 else "unknown"

        logger.info(f"FFmpeg found: {ffmpeg_path} (version {version})")
        return FFmpegInfo(available=True, path=ffmpeg_path, version=version)

    except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
        return FFmpegInfo(available=True, path=ffmpeg_path, version="unknown")


def check_ffmpeg_or_warn() -> bool:
    """Check for FFmpeg and log a warning if not found.

    Returns:
        True if FFmpeg is available, False otherwise.
    """
    info = detect_ffmpeg()
    if not info.available:
        logger.warning(
            "FFmpeg is not installed. Video/audio merging will not work. "
            "Install via: brew install ffmpeg (macOS) or download from ffmpeg.org"
        )
    return info.available
