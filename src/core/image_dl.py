"""Image Downloader — gallery-dl wrapper + direct HTTP fallback.

Implements DownloadEngine for image hosts and galleries using gallery-dl.
Supports Imgur, Flickr, DeviantArt, Reddit, Twitter images, Pinterest, etc.
Falls back to direct HTTP download for any URL ending in an image extension.
Always downloads at highest available resolution.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote

import requests
from PIL import Image as PILImage

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


# File extensions recognized as images
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    ".tiff", ".tif", ".avif", ".heic", ".heif", ".svg",
    ".jfif", ".pjpeg", ".pjp", ".ico",
}

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
# Note: Instagram excluded — yt-dlp handles it better (gallery-dl gets login-walled)
SOCIAL_IMAGE_DOMAINS = {
    "twitter.com", "x.com",
    "reddit.com", "www.reddit.com", "i.redd.it",
    "nitter.net",
}


def _is_image_url(url: str) -> bool:
    """Check if URL points directly to an image file."""
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path).lower()
        return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS)
    except Exception:
        return False


class ImageDownloader(DownloadEngine):
    """Download engine wrapping gallery-dl for image/gallery downloads.

    Handles image hosts, art communities, social media image posts,
    and direct image URLs from any website.
    Always selects the highest resolution available.
    """

    @property
    def name(self) -> str:
        return "gallery-dl"

    def can_handle(self, url: str) -> bool:
        """Check if this engine can handle the URL.

        Handles: known image domains, direct image URLs (by extension),
        and anything gallery-dl has an extractor for.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            domain_clean = domain[4:] if domain.startswith("www.") else domain

            # Direct image URL — always handle
            if _is_image_url(url):
                return True

            # Check known image domains
            if domain in IMAGE_DOMAINS or domain_clean in IMAGE_DOMAINS:
                return True
            if domain in SOCIAL_IMAGE_DOMAINS or domain_clean in SOCIAL_IMAGE_DOMAINS:
                return True

            # Try gallery-dl's own check
            try:
                from gallery_dl import extractor
                if extractor.find(url):
                    return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    def extract_info(self, url: str) -> MediaInfo:
        """Extract image metadata without downloading.

        Args:
            url: Image/gallery URL to extract info from.

        Returns:
            MediaInfo with available metadata.

        Raises:
            ExtractionError: If extraction fails.
        """
        # For direct image URLs, try a HEAD request for basic info
        if _is_image_url(url):
            return self._extract_direct_image_info(url)

        try:
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

            items = self._parse_gallery_dl_json(result.stdout)

            if not items:
                # gallery-dl returned data but no usable items — might be an error
                return MediaInfo(url=url, title="Image", media_type=MediaType.IMAGE)

            first = items[0]
            num_images = len(items)
            media_type = MediaType.GALLERY if num_images > 1 else MediaType.IMAGE

            return MediaInfo(
                url=url,
                title=first.get("title", first.get("filename", "Image")),
                description=first.get("description", ""),
                media_type=media_type,
                thumbnail_url=first.get("url"),
                width=first.get("width"),
                height=first.get("height"),
                filesize=first.get("filesize"),
                source_site=first.get("category", ""),
                uploader=first.get("author", first.get("uploader", "")),
                ext=first.get("extension", ""),
                extra={"num_images": num_images},
            )

        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to extract info from {url}: {e}") from e

    def _extract_direct_image_info(self, url: str) -> MediaInfo:
        """Extract info from a direct image URL via HEAD request."""
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            filename = Path(path).stem
            ext = Path(path).suffix.lstrip(".")

            # HEAD request for size info
            resp = requests.head(url, timeout=10, allow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
            filesize = None
            if resp.status_code == 200:
                content_length = resp.headers.get("Content-Length")
                if content_length:
                    filesize = int(content_length)

            return MediaInfo(
                url=url,
                title=filename or "Image",
                media_type=MediaType.IMAGE,
                thumbnail_url=url,
                filesize=filesize,
                source_site=parsed.netloc,
                ext=ext,
            )
        except Exception as e:
            raise ExtractionError(f"Failed to extract info from {url}: {e}") from e

    @staticmethod
    def _parse_gallery_dl_json(stdout: str) -> list[dict]:
        """Parse gallery-dl --dump-json output into metadata dicts.

        gallery-dl outputs a single JSON array of arrays. Each inner array
        has a type code at index 0:
          - Type 1/2: directory/config entries
          - Type 3: file entries with [3, url, metadata_dict]
          - Type -1: error entries
        """
        items: list[dict] = []
        try:
            data = json.loads(stdout)
            if not isinstance(data, list):
                return items
            for entry in data:
                if not isinstance(entry, list) or len(entry) < 2:
                    continue
                type_code = entry[0]
                # Type 3 = file entry: [3, url_string, metadata_dict]
                if type_code == 3 and len(entry) >= 3 and isinstance(entry[2], dict):
                    items.append(entry[2])
                # Type 2 = directory entry with metadata: [2, metadata_dict]
                elif type_code == 2 and isinstance(entry[1], dict):
                    # Only use if no file entries found later
                    if not items:
                        items.append(entry[1])
        except json.JSONDecodeError:
            # Try line-by-line parsing as fallback
            for line in stdout.strip().split("\n"):
                try:
                    entry = json.loads(line)
                    if isinstance(entry, list) and len(entry) >= 3 and isinstance(entry[2], dict):
                        if entry[0] != -1:  # Skip error entries
                            items.append(entry[2])
                except json.JSONDecodeError:
                    continue
        return items

    def download(self, url: str, options: Optional[DownloadOptions] = None) -> DownloadResult:
        """Download images from URL at highest quality.

        Tries gallery-dl first. For direct image URLs, falls back to
        direct HTTP download if gallery-dl fails.

        Args:
            url: Image/gallery URL to download.
            options: Download configuration.

        Returns:
            DownloadResult with success status and file paths.
        """
        opts = options or DownloadOptions()
        output_dir = opts.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Try gallery-dl first
        result = self._download_gallery_dl(url, opts, output_dir)
        if result.success:
            return result

        # Fall back to direct HTTP download for image URLs
        if _is_image_url(url):
            logger.info("gallery-dl failed, trying direct HTTP download for %s", url)
            return self._download_direct(url, opts, output_dir)

        return result

    def _download_gallery_dl(
        self, url: str, opts: DownloadOptions, output_dir: Path
    ) -> DownloadResult:
        """Download via gallery-dl subprocess."""
        existing_files = set(output_dir.rglob("*")) if output_dir.exists() else set()

        try:
            cmd = [sys.executable, "-m", "gallery_dl",
                   "--destination", str(output_dir)]

            # Cookie file BEFORE the -- separator
            if opts.cookies_file and opts.cookies_file.exists():
                cmd.extend(["--cookies", str(opts.cookies_file)])

            cmd.extend(["--", url])

            if opts.progress_callback:
                opts.progress_callback(DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    message=f"Downloading from {url}...",
                ))

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
            )

            current_files = set(output_dir.rglob("*")) if output_dir.exists() else set()
            new_files = sorted(current_files - existing_files)
            downloaded_files = [f for f in new_files if f.is_file()]

            if result.returncode != 0 and not downloaded_files:
                error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
                logger.warning("gallery-dl failed for %s: %s", url, error_msg)
                return DownloadResult(success=False, error=f"Download failed: {error_msg}")

            if opts.progress_callback:
                opts.progress_callback(DownloadProgress(
                    status=DownloadStatus.COMPLETED,
                    percent=100.0,
                    message=f"Downloaded {len(downloaded_files)} file(s)",
                ))

            filepath = downloaded_files[0] if downloaded_files else None
            media_type = MediaType.GALLERY if len(downloaded_files) > 1 else MediaType.IMAGE

            logger.info("Downloaded %d file(s) from %s", len(downloaded_files), url)
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
            logger.error("Download timed out for %s", url)
            return DownloadResult(success=False, error="Download timed out (5 min limit)")
        except Exception as e:
            logger.error("gallery-dl download failed for %s: %s", url, e)
            return DownloadResult(success=False, error=str(e))

    def _download_direct(
        self, url: str, opts: DownloadOptions, output_dir: Path
    ) -> DownloadResult:
        """Download an image directly via HTTP — works for any image URL."""
        try:
            if opts.progress_callback:
                opts.progress_callback(DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    message="Downloading image...",
                ))

            resp = requests.get(
                url, timeout=60, stream=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()

            # Determine filename from URL
            parsed = urlparse(url)
            path = unquote(parsed.path)
            filename = Path(path).name or "image.jpg"
            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in "._- ")[:200]
            if not filename:
                filename = "image.jpg"

            filepath = output_dir / filename
            # Avoid overwriting
            if filepath.exists() and opts.skip_existing:
                logger.info("File already exists: %s", filepath)
                return DownloadResult(
                    success=True, filepath=filepath,
                    media_info=MediaInfo(url=url, title=filepath.stem,
                                        media_type=MediaType.IMAGE,
                                        ext=filepath.suffix.lstrip(".")),
                    files_downloaded=[filepath],
                )

            # Download with 50MB limit
            max_size = 50 * 1024 * 1024
            downloaded = 0
            total = int(resp.headers.get("Content-Length", 0)) or None

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > max_size:
                        filepath.unlink(missing_ok=True)
                        return DownloadResult(success=False, error="File too large (>50MB)")
                    if opts.progress_callback and total:
                        opts.progress_callback(DownloadProgress(
                            status=DownloadStatus.DOWNLOADING,
                            percent=(downloaded / total) * 100,
                            downloaded_bytes=downloaded,
                            total_bytes=total,
                        ))

            if opts.progress_callback:
                opts.progress_callback(DownloadProgress(
                    status=DownloadStatus.COMPLETED,
                    percent=100.0,
                    message="Download complete",
                ))

            logger.info("Direct download complete: %s", filepath)
            return DownloadResult(
                success=True,
                filepath=filepath,
                media_info=MediaInfo(
                    url=url,
                    title=filepath.stem,
                    media_type=MediaType.IMAGE,
                    ext=filepath.suffix.lstrip("."),
                ),
                files_downloaded=[filepath],
            )

        except Exception as e:
            logger.error("Direct download failed for %s: %s", url, e)
            return DownloadResult(success=False, error=str(e))
