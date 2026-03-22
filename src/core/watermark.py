"""Watermark-Free Download Strategies.

Platform-specific logic to ensure downloads are free of watermarks.
Each platform has its own approach — some use yt-dlp options, some
modify the URL, some use alternative API endpoints.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def get_watermark_free_opts(url: str) -> dict:
    """Get yt-dlp options that avoid watermarks for a given URL.

    Args:
        url: The URL to customize options for.

    Returns:
        Dict of yt-dlp options to merge with defaults.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if "tiktok.com" in domain:
        return _tiktok_opts()
    elif "instagram.com" in domain:
        return _instagram_opts()
    elif "pinterest.com" in domain or "pin.it" in domain:
        return _pinterest_opts()
    elif "twitter.com" in domain or "x.com" in domain:
        return _twitter_opts()
    elif "reddit.com" in domain or "redd.it" in domain:
        return _reddit_opts()

    return {}


def _tiktok_opts() -> dict:
    """TikTok watermark-free options.

    yt-dlp natively selects the watermark-free stream for TikTok
    when the 'download' format is available. We ensure this by
    preferring the `download_addr` stream.
    """
    return {
        # Prefer the watermark-free stream that TikTok serves
        # via its API (usually the `download` format)
        "format": "download/bestvideo+bestaudio/best",
        # Use mobile API which often serves cleaner content
        "extractor_args": {
            "tiktok": {
                "api_hostname": ["api22-normal-c-useast2a.tiktokv.com"],
            }
        },
    }


def _instagram_opts() -> dict:
    """Instagram watermark-free options.

    Instagram content doesn't have watermarks by default.
    We just ensure we get the highest quality variant.
    """
    return {
        "format": "bestvideo+bestaudio/best",
    }


def _pinterest_opts() -> dict:
    """Pinterest watermark-free options.

    Pinterest images can be accessed at original resolution by
    modifying the URL path from /236x/ or /564x/ to /originals/.
    """
    return {
        "format": "best",
    }


def _twitter_opts() -> dict:
    """Twitter/X watermark-free options.

    Twitter content doesn't have watermarks. We ensure highest
    quality by requesting the original size.
    """
    return {
        "format": "bestvideo+bestaudio/best",
    }


def _reddit_opts() -> dict:
    """Reddit watermark-free options.

    Reddit video (v.redd.it) serves separate video+audio streams.
    FFmpeg is required to merge them.
    """
    return {
        "format": "bestvideo+bestaudio/best",
    }


def optimize_image_url(url: str) -> str:
    """Optimize an image URL to get the highest resolution version.

    Modifies known URL patterns to point to the original/full-res version.

    Args:
        url: The original image URL.

    Returns:
        Modified URL pointing to highest resolution, or original if unknown.
    """
    # Pinterest: swap thumbnail sizes for originals
    if "pinimg.com" in url:
        url = re.sub(r"/\d+x\d*v?\d*/", "/originals/", url)
        return url

    # Twitter: append :orig for original quality
    if "pbs.twimg.com" in url:
        if "?format=" in url:
            if "&name=" in url:
                url = re.sub(r"&name=\w+", "&name=orig", url)
            else:
                url += "&name=orig"
        elif ":orig" not in url and ":" not in url.split("/")[-1]:
            url += ":orig"
        return url

    # Instagram CDN: remove size constraints
    if "cdninstagram.com" in url or "instagram" in url:
        # Remove dimension parameters
        url = re.sub(r"/s\d+x\d+/", "/", url)
        return url

    # Reddit: use full resolution
    if "i.redd.it" in url:
        return url  # Already full resolution

    # Imgur: remove size suffix (e.g., "s", "m", "l", "h")
    if "imgur.com" in url:
        url = re.sub(r"([a-zA-Z0-9]+)[smlhbt]\.(\w+)$", r"\1.\2", url)
        return url

    return url
