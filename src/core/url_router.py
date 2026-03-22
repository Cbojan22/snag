"""URL Router — Detects URL type and routes to the correct download engine.

Given any URL, the router determines whether it's a video, image, or gallery
and dispatches to the appropriate engine (yt-dlp or gallery-dl).
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

from src.core.engine import (
    DownloadEngine,
    DownloadOptions,
    DownloadResult,
    ExtractionError,
    MediaInfo,
    MediaType,
)
from src.core.video_dl import VideoDownloader
from src.core.image_dl import ImageDownloader
from src.utils.clipboard import is_url

logger = logging.getLogger(__name__)


# URL patterns for direct image detection
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tiff", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".m4v"}

# Domains where yt-dlp is strongly preferred
VIDEO_FIRST_DOMAINS = {
    "youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com",
    "vimeo.com", "www.vimeo.com",
    "dailymotion.com", "www.dailymotion.com",
    "twitch.tv", "www.twitch.tv", "clips.twitch.tv",
    "tiktok.com", "www.tiktok.com", "vm.tiktok.com",
    "streamable.com",
    "v.redd.it",
    "bilibili.com", "www.bilibili.com",
    "nicovideo.jp",
    "mixcloud.com",
    "soundcloud.com",
    "bandcamp.com",
    "rumble.com",
    "bitchute.com",
    "odysee.com",
}

# Domains where gallery-dl is strongly preferred
IMAGE_FIRST_DOMAINS = {
    "imgur.com", "i.imgur.com",
    "flickr.com", "www.flickr.com",
    "deviantart.com", "www.deviantart.com",
    "artstation.com", "www.artstation.com",
    "pixiv.net", "www.pixiv.net",
    "danbooru.donmai.us",
    "gelbooru.com",
    "wallhaven.cc",
    "500px.com",
    "unsplash.com",
    "pexels.com",
    "pinterest.com", "www.pinterest.com", "pin.it",
}

# Social media where content could be either video or image
MIXED_CONTENT_DOMAINS = {
    "twitter.com", "x.com",
    "instagram.com", "www.instagram.com",
    "reddit.com", "www.reddit.com",
    "facebook.com", "www.facebook.com",
    "tumblr.com",
}


class URLRouter:
    """Routes URLs to the appropriate download engine.

    Strategy:
    1. Check if URL points directly to a media file (by extension)
    2. Check if domain is known video-first or image-first
    3. For mixed-content domains, try both engines
    4. For unknown URLs, try yt-dlp first (more generic), then gallery-dl
    """

    def __init__(self) -> None:
        self._video_engine = VideoDownloader()
        self._image_engine = ImageDownloader()
        self._engines: list[DownloadEngine] = [
            self._video_engine,
            self._image_engine,
        ]

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if a string is a valid URL."""
        return is_url(url)

    @staticmethod
    def clean_url(url: str) -> str:
        """Clean and normalize a URL."""
        url = url.strip()
        # Remove tracking parameters commonly appended
        # but keep the core URL intact
        return url

    def detect_media_type(self, url: str) -> MediaType:
        """Attempt to detect media type from URL alone.

        Args:
            url: The URL to analyze.

        Returns:
            Best-guess MediaType based on URL structure.
        """
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Check file extension
        for ext in IMAGE_EXTENSIONS:
            if path.endswith(ext):
                return MediaType.IMAGE

        for ext in VIDEO_EXTENSIONS:
            if path.endswith(ext):
                return MediaType.VIDEO

        # Check domain
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if domain in VIDEO_FIRST_DOMAINS:
            return MediaType.VIDEO
        if domain in IMAGE_FIRST_DOMAINS:
            return MediaType.IMAGE

        return MediaType.UNKNOWN

    def select_engine(self, url: str) -> DownloadEngine:
        """Select the best download engine for a URL.

        Args:
            url: URL to find an engine for.

        Returns:
            The most appropriate DownloadEngine.
        """
        media_type = self.detect_media_type(url)

        if media_type == MediaType.VIDEO:
            return self._video_engine
        elif media_type == MediaType.IMAGE:
            return self._image_engine

        # For mixed/unknown, check which engine can handle it
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if domain in MIXED_CONTENT_DOMAINS:
            # For social media, try to determine from URL structure
            path = parsed.path.lower()

            # Twitter/X: check for photo in path
            if ("twitter.com" in domain or "x.com" in domain):
                if "/photo/" in path:
                    return self._image_engine
                return self._video_engine  # Default to video for tweets

            # Instagram: reels are video, posts could be either
            if "instagram.com" in domain:
                if "/reel/" in path or "/tv/" in path:
                    return self._video_engine
                return self._image_engine  # Default to image for IG posts

            # Reddit: could be either
            if "reddit.com" in domain:
                if "v.redd.it" in url:
                    return self._video_engine
                if "i.redd.it" in url:
                    return self._image_engine
                return self._video_engine  # Default to video engine

        # Default: try yt-dlp first (it has the most generic extractors)
        if self._video_engine.can_handle(url):
            return self._video_engine
        if self._image_engine.can_handle(url):
            return self._image_engine

        # Last resort: return video engine (yt-dlp has generic fallback)
        return self._video_engine

    def extract_info(self, url: str) -> MediaInfo:
        """Extract metadata from URL using the best engine.

        Args:
            url: URL to extract info from.

        Returns:
            MediaInfo from the selected engine.

        Raises:
            ExtractionError: If all engines fail.
        """
        engine = self.select_engine(url)
        logger.info(f"Using {engine.name} to extract info from {url}")

        try:
            return engine.extract_info(url)
        except ExtractionError:
            # If primary engine fails, try the other one
            fallback = (
                self._image_engine if engine is self._video_engine
                else self._video_engine
            )
            logger.info(f"Falling back to {fallback.name} for {url}")
            try:
                return fallback.extract_info(url)
            except ExtractionError:
                raise ExtractionError(f"No engine could extract info from {url}")

    def download(self, url: str, options: Optional[DownloadOptions] = None) -> DownloadResult:
        """Download media from URL using the best engine.

        Tries the primary engine first, falls back to alternate
        if the primary fails.

        Args:
            url: URL to download from.
            options: Download configuration.

        Returns:
            DownloadResult from whichever engine succeeds.
        """
        engine = self.select_engine(url)
        logger.info(f"Using {engine.name} to download {url}")

        result = engine.download(url, options)

        if not result.success:
            # Try fallback engine
            fallback = (
                self._image_engine if engine is self._video_engine
                else self._video_engine
            )
            logger.info(f"Primary engine failed, trying {fallback.name} for {url}")
            fallback_result = fallback.download(url, options)

            if fallback_result.success:
                return fallback_result

            # Both failed — return the primary error
            logger.error(f"All engines failed for {url}")

        return result
