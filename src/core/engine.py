"""Download Engine — Abstract base class for all download backends.

Every download backend (yt-dlp, gallery-dl, etc.) implements this
interface so the URL router can treat them uniformly.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Optional


logger = logging.getLogger(__name__)


class MediaType(Enum):
    """Type of media being downloaded."""
    VIDEO = auto()
    IMAGE = auto()
    AUDIO = auto()
    GALLERY = auto()  # Multiple images
    UNKNOWN = auto()


class DownloadStatus(Enum):
    """Status of a download task."""
    PENDING = auto()
    EXTRACTING = auto()
    DOWNLOADING = auto()
    PROCESSING = auto()  # Post-processing (merge, convert)
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class MediaInfo:
    """Metadata extracted from a URL before downloading."""
    url: str
    title: str = "Unknown"
    description: str = ""
    media_type: MediaType = MediaType.UNKNOWN
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None  # seconds, for video/audio
    width: Optional[int] = None
    height: Optional[int] = None
    filesize: Optional[int] = None  # bytes, if known
    format_note: str = ""
    source_site: str = ""
    uploader: str = ""
    ext: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def resolution(self) -> str:
        """Human-readable resolution string."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Unknown"

    @property
    def filesize_human(self) -> str:
        """Human-readable file size."""
        if not self.filesize:
            return "Unknown"
        size = float(self.filesize)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


@dataclass
class DownloadProgress:
    """Progress update for an active download."""
    status: DownloadStatus = DownloadStatus.PENDING
    percent: float = 0.0  # 0-100
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed: Optional[float] = None  # bytes/sec
    eta: Optional[float] = None  # seconds remaining
    filename: str = ""
    message: str = ""

    @property
    def speed_human(self) -> str:
        """Human-readable download speed."""
        if not self.speed:
            return ""
        if self.speed < 1024:
            return f"{self.speed:.0f} B/s"
        elif self.speed < 1024 * 1024:
            return f"{self.speed / 1024:.1f} KB/s"
        else:
            return f"{self.speed / (1024 * 1024):.1f} MB/s"


ProgressCallback = Callable[[DownloadProgress], None]


@dataclass
class DownloadOptions:
    """Options for a download operation."""
    output_dir: Path = field(default_factory=lambda: Path.home() / "Downloads" / "Snag")
    filename_template: str = "%(title)s.%(ext)s"
    prefer_mp4: bool = True
    max_quality: bool = True  # Always highest quality
    audio_only: bool = False  # Extract audio as MP3
    skip_existing: bool = True
    write_thumbnail: bool = False
    embed_metadata: bool = True
    progress_callback: Optional[ProgressCallback] = None
    cookies_file: Optional[Path] = None


@dataclass
class DownloadResult:
    """Result of a completed download."""
    success: bool
    filepath: Optional[Path] = None
    media_info: Optional[MediaInfo] = None
    error: Optional[str] = None
    files_downloaded: list[Path] = field(default_factory=list)


class DownloadEngine(ABC):
    """Abstract base class for download backends.

    All download engines (yt-dlp, gallery-dl, etc.) must implement
    this interface to be usable by the URL router.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable engine name."""
        ...

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this engine can handle the given URL.

        Args:
            url: The URL to check.
        """
        ...

    @abstractmethod
    def extract_info(self, url: str) -> MediaInfo:
        """Extract metadata from a URL without downloading.

        Args:
            url: The URL to extract info from.

        Returns:
            MediaInfo object with metadata.

        Raises:
            ExtractionError: If the URL cannot be processed.
        """
        ...

    @abstractmethod
    def download(self, url: str, options: Optional[DownloadOptions] = None) -> DownloadResult:
        """Download the media at the given URL.

        Args:
            url: The URL to download.
            options: Download options.

        Returns:
            DownloadResult with success/failure and file path.
        """
        ...


class ExtractionError(Exception):
    """Raised when a URL cannot be extracted (invalid, unsupported, etc.)."""
    pass
