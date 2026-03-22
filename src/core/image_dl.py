"""Image Downloader — gallery-dl wrapper.

Implements DownloadEngine for image hosts and galleries using gallery-dl.
Supports Imgur, Flickr, DeviantArt, Reddit, Twitter images, Pinterest, etc.
Always downloads at highest available resolution.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from src.core.engine import (
    DownloadEngine,
    DownloadOptions,
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    ExtractionError,
    MediaInfo,
    MediaType,
)

logger = logging.getLogger(__name__)


# Known image-focused domains that gallery-dl handles well
IMAGE_DOMAINS = {
    "imgur.com", "i.imgur.com",
    "flickr.com", "www.flickr.com",
    "deviantart.com", "www.deviantart.com",
    "artstation.com", "www.artstation.com",
    "pixiv.net", "www.pixiv.net",
    "danbooru.donmai.us",
    "gelbooru.com",
    "tumblr.com",
    "pinterest.com", "www.pinterest.com", "pin.it",
    "500px.com",
    "unsplash.com",
    "pexels.com",
    "wallhaven.cc",
}

# Social media domains where gallery-dl handles images
SOCIAL_IMAGE_DOMAINS = {
    "instagram.com", "www.instagram.com",
    "twitter.com", "x.com",
    "reddit.com", "www.reddit.com", "i.redd.it",
    "nitter.net",
}


class ImageDownloader(DownloadEngine):
    """Download engine wrapping gallery-dl for image/gallery downloads.

    Handles image hosts, art communities, and social media image posts.
    Always selects the highest resolution available.
    """

    @property
    def name(self) -> str:
        return "gallery-dl"

    def can_handle(self, url: str) -> bool:
        """Check if gallery-dl supports this URL.

        Checks against known image domains and gallery-dl's
        built-in extractor list.
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix for matching
            if domain.startswith("www."):
                domain_clean = domain[4:]
            else:
                domain_clean = domain

            # Check known image domains
            if domain in IMAGE_DOMAINS or domain_clean in IMAGE_DOMAINS:
                return True
            if domain in SOCIAL_IMAGE_DOMAINS or domain_clean in SOCIAL_IMAGE_DOMAINS:
                return True

            # Try gallery-dl's own check
            try:
                import gallery_dl
                from gallery_dl import extractor
                if extractor.find(url):
                    return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    def _build_config(self, options: Optional[DownloadOptions] = None) -> dict:
        """Build gallery-dl configuration dict."""
        opts = options or DownloadOptions()
        output_dir = opts.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "extractor": {
                "base-directory": str(output_dir),
                "skip": opts.skip_existing,
                "image-range": None,  # Download all images
                # Twitter-specific: get original quality
                "twitter": {
                    "text-tweets": False,
                    "retweets": False,
                    "content": True,
                    "size": "orig",  # Original size images
                },
                # Reddit-specific
                "reddit": {
                    "comments": 0,
                    "morecomments": False,
                },
                # Instagram-specific
                "instagram": {
                    "include": "posts",
                },
                # Imgur-specific
                "imgur": {
                    "mp4": False,  # Keep images as images
                },
            },
        }

        # Cookie file for authenticated downloads
        if opts.cookies_file and opts.cookies_file.exists():
            config["extractor"]["cookies"] = str(opts.cookies_file)

        return config

    def extract_info(self, url: str) -> MediaInfo:
        """Extract image metadata without downloading.

        Uses gallery-dl to probe the URL for metadata.

        Args:
            url: Image/gallery URL to extract info from.

        Returns:
            MediaInfo with available metadata.

        Raises:
            ExtractionError: If extraction fails.
        """
        try:
            # Use gallery-dl CLI to dump JSON info
            result = subprocess.run(
                [sys.executable, "-m", "gallery_dl", "--dump-json", "--", url],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise ExtractionError(
                    f"gallery-dl extraction failed: {result.stderr[:500]}"
                )

            # Parse the first JSON object (might be multiple for galleries)
            lines = result.stdout.strip().split("\n")
            items = []
            for line in lines:
                try:
                    data = json.loads(line)
                    if isinstance(data, list) and len(data) >= 3:
                        items.append(data)
                except json.JSONDecodeError:
                    continue

            if not items:
                return MediaInfo(url=url, title="Image", media_type=MediaType.IMAGE)

            # Use first item for metadata
            first = items[0]
            metadata = first[2] if len(first) > 2 and isinstance(first[2], dict) else {}

            num_images = len(items)
            media_type = MediaType.GALLERY if num_images > 1 else MediaType.IMAGE

            return MediaInfo(
                url=url,
                title=metadata.get("title", metadata.get("filename", "Image")),
                description=metadata.get("description", ""),
                media_type=media_type,
                thumbnail_url=metadata.get("url"),
                width=metadata.get("width"),
                height=metadata.get("height"),
                filesize=metadata.get("filesize"),
                source_site=metadata.get("category", ""),
                uploader=metadata.get("author", metadata.get("uploader", "")),
                ext=metadata.get("extension", ""),
                extra={"num_images": num_images, "raw_metadata": metadata},
            )

        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to extract info from {url}: {e}") from e

    def download(self, url: str, options: Optional[DownloadOptions] = None) -> DownloadResult:
        """Download images from URL at highest quality.

        Args:
            url: Image/gallery URL to download.
            options: Download configuration.

        Returns:
            DownloadResult with success status and file paths.
        """
        opts = options or DownloadOptions()
        config = self._build_config(opts)
        output_dir = opts.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Track files before download to find new ones
        existing_files = set(output_dir.rglob("*")) if output_dir.exists() else set()

        try:
            # Build CLI args for gallery-dl
            cmd = [
                sys.executable, "-m", "gallery_dl",
                "--destination", str(output_dir),
                "--", url,
            ]

            # Add cookie file if present
            if opts.cookies_file and opts.cookies_file.exists():
                cmd.extend(["--cookies", str(opts.cookies_file)])

            # Notify progress callback that download is starting
            if opts.progress_callback:
                opts.progress_callback(DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    message=f"Downloading images from {url}...",
                ))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Find newly downloaded files
            current_files = set(output_dir.rglob("*")) if output_dir.exists() else set()
            new_files = sorted(current_files - existing_files)
            downloaded_files = [f for f in new_files if f.is_file()]

            if result.returncode != 0 and not downloaded_files:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                logger.error(f"gallery-dl failed for {url}: {error_msg}")
                return DownloadResult(
                    success=False,
                    error=f"Download failed: {error_msg}",
                )

            # Notify completion
            if opts.progress_callback:
                opts.progress_callback(DownloadProgress(
                    status=DownloadStatus.COMPLETED,
                    percent=100.0,
                    message=f"Downloaded {len(downloaded_files)} file(s)",
                ))

            filepath = downloaded_files[0] if downloaded_files else None
            media_type = MediaType.GALLERY if len(downloaded_files) > 1 else MediaType.IMAGE

            logger.info(f"Downloaded {len(downloaded_files)} file(s) from {url}")
            return DownloadResult(
                success=True,
                filepath=filepath,
                media_info=MediaInfo(
                    url=url,
                    title=filepath.stem if filepath else "Image",
                    media_type=media_type,
                    ext=filepath.suffix.lstrip(".") if filepath else "",
                ),
                files_downloaded=downloaded_files,
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Download timed out for {url}")
            return DownloadResult(success=False, error="Download timed out (5 min limit)")
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            return DownloadResult(success=False, error=str(e))
