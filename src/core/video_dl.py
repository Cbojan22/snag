"""Video Downloader — yt-dlp wrapper.

Implements DownloadEngine for video platforms using yt-dlp.
Supports 1000+ sites, always selects highest quality, handles
watermark-free TikTok downloads, and merges video+audio via FFmpeg.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yt_dlp

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
from src.core.watermark import get_watermark_free_opts

logger = logging.getLogger(__name__)


class VideoDownloader(DownloadEngine):
    """Download engine wrapping yt-dlp for video/audio downloads.

    Supports YouTube, TikTok, Twitter/X, Vimeo, Reddit, and 1000+
    other platforms. Always selects the highest quality available.
    """

    @property
    def name(self) -> str:
        return "yt-dlp"

    def can_handle(self, url: str) -> bool:
        """Check if yt-dlp has a non-generic extractor for this URL."""
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                for ie in ydl._ies:
                    if ie.suitable(url) and ie.ie_key() != "Generic":
                        return True
            return False
        except Exception:
            return False

    def _build_opts(self, url: str, options: Optional[DownloadOptions] = None) -> dict:
        """Build yt-dlp options dict from DownloadOptions."""
        opts = options or DownloadOptions()
        output_dir = opts.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Format selection: prefer H.264 (avc1) for universal playback
        # (AV1/VP9 are higher quality but QuickTime/many players can't open them)
        if opts.prefer_mp4:
            fmt = (
                "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/"
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo+bestaudio/best"
            )
        else:
            fmt = "bestvideo+bestaudio/best"

        ydl_opts: dict = {
            "format": fmt,
            "merge_output_format": "mp4" if opts.prefer_mp4 else None,
            "outtmpl": str(output_dir / opts.filename_template),
            # Behavior
            "noplaylist": False,
            "ignoreerrors": False,
            "no_warnings": False,
            "overwrites": not opts.skip_existing,
            # Metadata
            "writethumbnail": opts.write_thumbnail,
            "postprocessors": [],
            # Logging
            "quiet": False,
            "no_color": True,
        }

        # Embed metadata if requested
        if opts.embed_metadata:
            ydl_opts["postprocessors"].append({
                "key": "FFmpegMetadata",
            })

        # Cookie file for authenticated downloads
        if opts.cookies_file and opts.cookies_file.exists():
            ydl_opts["cookiefile"] = str(opts.cookies_file)

        # Progress hook
        if opts.progress_callback:
            ydl_opts["progress_hooks"] = [
                self._make_progress_hook(opts.progress_callback)
            ]

        # Merge platform-specific watermark-free options
        wm_opts = get_watermark_free_opts(url)
        ydl_opts.update(wm_opts)

        return ydl_opts

    @staticmethod
    def _make_progress_hook(callback):
        """Create a yt-dlp progress hook that calls our callback."""
        def hook(d):
            status_map = {
                "downloading": DownloadStatus.DOWNLOADING,
                "finished": DownloadStatus.PROCESSING,
                "error": DownloadStatus.FAILED,
            }
            progress = DownloadProgress(
                status=status_map.get(d.get("status", ""), DownloadStatus.DOWNLOADING),
                percent=d.get("_percent_str", 0),
                downloaded_bytes=d.get("downloaded_bytes", 0),
                total_bytes=d.get("total_bytes") or d.get("total_bytes_estimate"),
                speed=d.get("speed"),
                eta=d.get("eta"),
                filename=d.get("filename", ""),
            )
            # Parse percent from string if needed
            if isinstance(progress.percent, str):
                try:
                    progress.percent = float(progress.percent.strip().rstrip("%"))
                except (ValueError, AttributeError):
                    progress.percent = 0.0
            callback(progress)
        return hook

    def extract_info(self, url: str) -> MediaInfo:
        """Extract video metadata without downloading.

        Args:
            url: Video URL to extract info from.

        Returns:
            MediaInfo with title, resolution, duration, etc.

        Raises:
            ExtractionError: If extraction fails.
        """
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                raise ExtractionError(f"No info extracted from {url}")

            # Determine best format dimensions
            width = info.get("width")
            height = info.get("height")

            # If not directly available, check formats
            if not width or not height:
                formats = info.get("formats", [])
                if formats:
                    # Find the best video format
                    video_formats = [f for f in formats if f.get("vcodec") != "none"]
                    if video_formats:
                        best = max(
                            video_formats,
                            key=lambda f: (f.get("height") or 0) * (f.get("width") or 0),
                        )
                        width = best.get("width")
                        height = best.get("height")

            return MediaInfo(
                url=url,
                title=info.get("title", "Unknown"),
                description=info.get("description", ""),
                media_type=MediaType.VIDEO,
                thumbnail_url=info.get("thumbnail"),
                duration=info.get("duration"),
                width=width,
                height=height,
                filesize=info.get("filesize") or info.get("filesize_approx"),
                format_note=info.get("format_note", ""),
                source_site=info.get("extractor", ""),
                uploader=info.get("uploader", ""),
                ext=info.get("ext", "mp4"),
                extra={
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "upload_date": info.get("upload_date"),
                    "webpage_url": info.get("webpage_url"),
                },
            )
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Failed to extract info from {url}: {e}") from e

    def download(self, url: str, options: Optional[DownloadOptions] = None) -> DownloadResult:
        """Download video from URL at highest quality.

        Args:
            url: Video URL to download.
            options: Download configuration.

        Returns:
            DownloadResult with success status and file path.
        """
        opts = options or DownloadOptions()
        ydl_opts = self._build_opts(url, opts)
        downloaded_files: list[Path] = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if not info:
                    return DownloadResult(success=False, error=f"No info returned for {url}")

                # Find the downloaded file (must be inside `with` block)
                filename = ydl.prepare_filename(info)

            filepath = Path(filename)

            # yt-dlp may change the extension after post-processing
            if not filepath.exists():
                # Try with .mp4 extension
                mp4_path = filepath.with_suffix(".mp4")
                if mp4_path.exists():
                    filepath = mp4_path

            downloaded_files.append(filepath)

            media_info = MediaInfo(
                url=url,
                title=info.get("title", "Unknown"),
                media_type=MediaType.VIDEO,
                width=info.get("width"),
                height=info.get("height"),
                ext=filepath.suffix.lstrip("."),
                source_site=info.get("extractor", ""),
            )

            logger.info(f"Downloaded: {filepath}")
            return DownloadResult(
                success=True,
                filepath=filepath,
                media_info=media_info,
                files_downloaded=downloaded_files,
            )

        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            return DownloadResult(
                success=False,
                error=str(e),
                files_downloaded=downloaded_files,
            )
