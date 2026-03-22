"""Video Downloader — yt-dlp wrapper.

Implements DownloadEngine for video platforms using yt-dlp.
Supports 1000+ sites, always selects highest quality, handles
watermark-free TikTok downloads, and merges video+audio via FFmpeg.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
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

        postprocessors: list[dict] = []

        if opts.audio_only:
            # Audio-only: grab best audio, convert to MP3 320kbps
            fmt = "bestaudio/best"
            merge_format = None
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            })
        elif opts.prefer_mp4:
            # MP4 mode: prefer H.264 for compatibility, but fall back to
            # any codec and let FFmpeg transcode — never sacrifice resolution
            fmt = (
                "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[vcodec^=avc1]+bestaudio/"
                "bestvideo[ext=mp4]+bestaudio/"
                "bestvideo+bestaudio/best"
            )
            merge_format = "mp4"
        else:
            # Best possible quality — any codec (VP9, AV1, etc.)
            fmt = "bestvideo+bestaudio/best"
            merge_format = None

        ydl_opts: dict = {
            "format": fmt,
            "merge_output_format": merge_format,
            "outtmpl": str(output_dir / opts.filename_template),
            # Behavior
            "noplaylist": False,
            "ignoreerrors": False,
            "no_warnings": False,
            "overwrites": not opts.skip_existing,
            # Metadata
            "writethumbnail": opts.write_thumbnail,
            "postprocessors": postprocessors,
            # Logging
            "quiet": False,
            "no_color": True,
        }

        # Explicitly set ffmpeg location so bundled apps find ffmpeg/ffprobe
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            ydl_opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)

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

    @staticmethod
    def _is_twitter_url(url: str) -> bool:
        """Check if URL is a Twitter/X tweet."""
        domain = urlparse(url).netloc.lower()
        return ("twitter.com" in domain or "x.com" in domain)

    def _download_twitter_video(self, url: str, opts: DownloadOptions) -> Optional[DownloadResult]:
        """Download video from Twitter/X using the fxtwitter API.

        Fallback for when yt-dlp's Twitter extractor is broken
        (which happens periodically as Twitter changes their API).
        Returns None if the tweet has no video.
        """
        # Extract tweet ID from URL
        match = re.search(r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', url)
        if not match:
            return None

        user, tweet_id = match.group(1), match.group(2)
        output_dir = opts.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # fxtwitter API reliably returns JSON (unlike vxtwitter which returns HTML)
            # Using /i/ as user works — fxtwitter resolves the actual user from tweet ID
            api_url = f"https://api.fxtwitter.com/{user}/status/{tweet_id}"
            resp = requests.get(api_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
            })

            if resp.status_code != 200:
                return None

            try:
                data = resp.json()
            except Exception:
                return None

            tweet = data.get("tweet")
            if not tweet:
                return None

            # Find video URL from fxtwitter media structure
            video_url = None
            media = tweet.get("media", {})
            for item in media.get("all", []):
                if item.get("type") in ("video", "gif"):
                    video_url = item.get("url")
                    break

            # Also check videos list
            if not video_url:
                for vid in media.get("videos", []):
                    video_url = vid.get("url")
                    if video_url:
                        break

            if not video_url:
                return None

            title = tweet.get("text", "tweet")[:60].strip()
            safe_title = re.sub(r'[^\w -]', '', title.replace('\n', ' ')).strip()[:50] or "tweet"

            if opts.progress_callback:
                opts.progress_callback(DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    message="Downloading from Twitter...",
                ))

            # Download the video file
            video_resp = requests.get(video_url, timeout=120, stream=True, headers={
                "User-Agent": "Mozilla/5.0",
            })
            video_resp.raise_for_status()

            filepath = output_dir / f"{safe_title}.mp4"
            total = int(video_resp.headers.get("Content-Length", 0)) or None
            downloaded = 0

            with open(filepath, "wb") as f:
                for chunk in video_resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if opts.progress_callback and total:
                        opts.progress_callback(DownloadProgress(
                            status=DownloadStatus.DOWNLOADING,
                            percent=(downloaded / total) * 100,
                            downloaded_bytes=downloaded,
                            total_bytes=total,
                        ))

            # If audio_only, convert to MP3 using ffmpeg
            if opts.audio_only:
                ffmpeg_path = shutil.which("ffmpeg")
                if ffmpeg_path:
                    mp3_path = filepath.with_suffix(".mp3")
                    if opts.progress_callback:
                        opts.progress_callback(DownloadProgress(
                            status=DownloadStatus.PROCESSING,
                            message="Converting to MP3...",
                        ))
                    result = subprocess.run(
                        [ffmpeg_path, "-i", str(filepath), "-vn",
                         "-acodec", "libmp3lame", "-ab", "320k",
                         "-y", str(mp3_path)],
                        capture_output=True, timeout=120,
                    )
                    if result.returncode == 0 and mp3_path.exists():
                        filepath.unlink(missing_ok=True)
                        filepath = mp3_path
                    else:
                        logger.warning("MP3 conversion failed, keeping MP4")

            if opts.progress_callback:
                opts.progress_callback(DownloadProgress(
                    status=DownloadStatus.COMPLETED,
                    percent=100.0,
                    message="Download complete",
                ))

            is_audio = filepath.suffix.lower() == ".mp3"
            logger.info("Downloaded Twitter video: %s", filepath)
            return DownloadResult(
                success=True,
                filepath=filepath,
                media_info=MediaInfo(
                    url=url,
                    title=safe_title,
                    media_type=MediaType.AUDIO if is_audio else MediaType.VIDEO,
                    ext=filepath.suffix.lstrip("."),
                    source_site="twitter",
                ),
                files_downloaded=[filepath],
            )

        except Exception as e:
            logger.error("Twitter video fallback failed for %s: %s", url, e)
            return None

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
                # Try common extensions after conversion
                for try_ext in (".mp4", ".mp3", ".webm", ".mkv"):
                    alt = filepath.with_suffix(try_ext)
                    if alt.exists():
                        filepath = alt
                        break

            downloaded_files.append(filepath)

            is_audio = opts.audio_only or filepath.suffix.lower() == ".mp3"
            media_info = MediaInfo(
                url=url,
                title=info.get("title", "Unknown"),
                media_type=MediaType.AUDIO if is_audio else MediaType.VIDEO,
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
            logger.error(f"yt-dlp failed for {url}: {e}")

            # Twitter/X fallback: use vxtwitter API when yt-dlp's extractor is broken
            if self._is_twitter_url(url):
                logger.info("Trying Twitter video fallback for %s", url)
                twitter_result = self._download_twitter_video(url, opts)
                if twitter_result:
                    return twitter_result

            return DownloadResult(
                success=False,
                error=str(e),
                files_downloaded=downloaded_files,
            )
