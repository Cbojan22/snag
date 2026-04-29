"""Main application window — assembles all UI components."""

import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Optional

import customtkinter as ctk
import requests

from src.core.engine import (
    DownloadOptions,
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    MediaInfo,
)
from src.core.url_router import URLRouter
from src.ui.history import HistoryEntry, HistoryPanel
from src.ui.preview import PreviewPanel
from src.ui.progress import ProgressPanel
from src.ui.settings import SettingsPanel
from src.ui.styles import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_HIGHLIGHT,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TEXT_MUTED,
    FONT_LOGO,
    FONT_LOGO_GLYPH,
    FONT_MONO_SM,
    FONT_MONO_TAG,
    FONT_SMALL,
    PAD_LG,
    PAD_MD,
    PAD_SM,
    PAD_XS,
    PAD_XL,
    PAD_2XL,
    WINDOW_DEFAULT_SIZE,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
)
from src.ui.url_input import URLInputBar
from src.utils.clipboard import ClipboardMonitor
from src.utils.ffmpeg import check_ffmpeg_or_warn
from src.utils.filesystem import ensure_download_dir

logger = logging.getLogger(__name__)


class MainWindow:
    """Top-level application window."""

    def __init__(self) -> None:
        self._router = URLRouter()
        self._clipboard_monitor: Optional[ClipboardMonitor] = None
        self._current_info: Optional[MediaInfo] = None
        self._preview_url: Optional[str] = None

        self._init_window()
        self._build_layout()
        self._start_clipboard_monitor()
        check_ffmpeg_or_warn()

    def _init_window(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._root = ctk.CTk()
        self._root.title(WINDOW_TITLE)
        self._root.geometry(WINDOW_DEFAULT_SIZE)
        self._root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self._root.configure(fg_color=COLOR_BG)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        self._root.grid_columnconfigure(0, weight=1)

        # ── Header ────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self._root, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=PAD_XL, pady=(PAD_2XL, 0), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        # Build pill above the wordmark
        version_pill = ctk.CTkLabel(
            header_frame,
            text="v0.2  \u2022  MEDIA RIPPER",
            font=FONT_MONO_TAG,
            text_color=COLOR_HIGHLIGHT,
            anchor="w",
        )
        version_pill.grid(row=0, column=0, sticky="w", pady=(0, PAD_SM))

        # Wordmark row \u2014 lime caret + Futura bold "snag"
        logo_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_row.grid(row=1, column=0, sticky="w")

        caret = ctk.CTkLabel(
            logo_row,
            text="\u25b8",  # right-pointing solid triangle as a play/snag mark
            font=FONT_LOGO_GLYPH,
            text_color=COLOR_ACCENT,
        )
        caret.grid(row=0, column=0, padx=(0, PAD_SM), sticky="sw", pady=(0, 18))

        wordmark = ctk.CTkLabel(
            logo_row,
            text="snag",
            font=FONT_LOGO,
            text_color=COLOR_TEXT,
            anchor="w",
        )
        wordmark.grid(row=0, column=1, sticky="w")

        # Lime accent underline anchors the wordmark
        accent_bar = ctk.CTkFrame(
            header_frame,
            fg_color=COLOR_ACCENT,
            height=3,
            corner_radius=2,
            width=64,
        )
        accent_bar.grid(row=2, column=0, sticky="w", pady=(0, PAD_SM))
        accent_bar.grid_propagate(False)

        subtitle = ctk.CTkLabel(
            header_frame,
            text="grab any media from the web \u2014 highest quality, no watermarks",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        )
        subtitle.grid(row=3, column=0, pady=(PAD_SM, 0), sticky="w")

        # ── URL Input ─────────────────────────────────────────────
        self._url_input = URLInputBar(
            self._root,
            on_submit=self._on_url_submitted,
            on_url_changed=self._on_url_changed,
        )
        self._url_input.grid(
            row=2, column=0, padx=PAD_XL, pady=(PAD_MD, PAD_SM), sticky="ew"
        )

        # ── Preview ───────────────────────────────────────────────
        self._preview = PreviewPanel(self._root)
        self._preview.grid(
            row=3, column=0, padx=PAD_XL, pady=(0, PAD_MD), sticky="ew"
        )

        # ── Downloads section header ──────────────────────────────
        dl_header_row = ctk.CTkFrame(self._root, fg_color="transparent")
        dl_header_row.grid(row=4, column=0, padx=PAD_XL, pady=(PAD_MD, PAD_XS), sticky="ew")
        dl_header_row.grid_columnconfigure(1, weight=1)

        dl_dot = ctk.CTkLabel(
            dl_header_row,
            text="●",
            font=FONT_MONO_SM,
            text_color=COLOR_ACCENT,
        )
        dl_dot.grid(row=0, column=0, padx=(2, PAD_SM), sticky="w")

        downloads_header = ctk.CTkLabel(
            dl_header_row,
            text="DOWNLOADS",
            font=FONT_MONO_TAG,
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        )
        downloads_header.grid(row=0, column=1, sticky="w")

        # Progress panel (scrollable, fills remaining space)
        self._progress = ProgressPanel(self._root)
        self._progress.grid(
            row=5, column=0, padx=PAD_XL, pady=(PAD_SM, PAD_SM), sticky="nsew"
        )
        self._root.grid_rowconfigure(5, weight=1)

        # ── Bottom bar ────────────────────────────────────────────
        bottom = ctk.CTkFrame(self._root, fg_color="transparent")
        bottom.grid(row=6, column=0, padx=PAD_XL, pady=(0, PAD_SM), sticky="ew")
        bottom.grid_columnconfigure(0, weight=1)

        self._settings = SettingsPanel(
            bottom,
            on_settings_changed=self._on_settings_changed,
        )
        self._settings.grid(row=0, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # URL submission and download orchestration
    # ------------------------------------------------------------------

    def _on_url_changed(self, url: str) -> None:
        """Handle URL change in the input — fetch preview immediately."""
        if url == self._preview_url:
            return
        self._preview_url = url
        self._current_info = None
        self._preview.set_loading()

        thread = threading.Thread(
            target=self._extract_preview,
            args=(url,),
            daemon=True,
        )
        thread.start()

    def _extract_preview(self, url: str) -> None:
        """Background thread: extract info and show preview."""
        # If URL changed while we were working, bail out
        if url != self._preview_url:
            return
        try:
            info = self._router.extract_info(url)
            if url != self._preview_url:
                return
            self._current_info = info
            self._root.after(0, self._preview.update_info, info)
            self._fetch_thumbnail(info)
        except Exception as exc:
            logger.debug("Preview extraction failed: %s", exc)
            if url == self._preview_url:
                self._root.after(0, self._preview.set_unavailable)

    def _on_url_submitted(self, url: str) -> None:
        """Handle a URL submission: download (preview already shown)."""
        logger.info("Processing URL: %s", url)
        self._url_input.set_enabled(False)

        # Trigger preview if not already loaded for this URL
        if url != self._preview_url:
            self._on_url_changed(url)

        download_id = str(uuid.uuid4())[:8]
        self._start_download_ui(download_id, url)

        thread = threading.Thread(
            target=self._process_url,
            args=(url, download_id),
            daemon=True,
        )
        thread.start()

    def _process_url(self, url: str, download_id: str) -> None:
        """Background thread: download media (preview extracted separately)."""
        # Use already-extracted info if available, otherwise extract now
        info = self._current_info
        if not info or (info and info.url != url):
            try:
                info = self._router.extract_info(url)
                self._current_info = info
                self._root.after(0, self._preview.update_info, info)
                self._fetch_thumbnail(info)
            except Exception as exc:
                logger.debug("Info extraction failed: %s", exc)

        # Update download card title with real title
        if info and info.title:
            card = self._progress.get_card(download_id)
            if card:
                self._root.after(0, card.set_title, info.title)

        # Download
        output_dir = Path(self._settings.get_download_dir())

        options = DownloadOptions(
            output_dir=output_dir,
            prefer_mp4=True,
            audio_only=self._settings.get_audio_only(),
            progress_callback=lambda p: self._root.after(
                0, self._on_progress, download_id, p
            ),
        )

        try:
            ensure_download_dir(output_dir)
            self._root.after(
                0, self._update_status, download_id, DownloadStatus.DOWNLOADING
            )
            result = self._router.download(url, options)

            if result.success:
                self._root.after(
                    0, self._on_download_complete, download_id, url, result
                )
            else:
                self._root.after(
                    0, self._on_download_failed, download_id, result.error or "Unknown error"
                )
        except Exception as exc:
            logger.exception("Download failed: %s", exc)
            self._root.after(
                0, self._on_download_failed, download_id, str(exc)
            )
        finally:
            self._root.after(0, self._url_input.set_enabled, True)

    def _fetch_thumbnail(self, info: MediaInfo) -> None:
        """Download and display thumbnail image."""
        if not info.thumbnail_url:
            return
        try:
            resp = requests.get(info.thumbnail_url, timeout=10, stream=True)
            if resp.status_code == 200:
                # Limit to 5 MB to prevent memory issues
                data = resp.raw.read(5 * 1024 * 1024)
                self._root.after(
                    0, self._preview.set_thumbnail_from_bytes, data
                )
        except Exception:
            logger.debug("Thumbnail fetch failed")

    # ------------------------------------------------------------------
    # Progress / status UI updates (called on main thread via after())
    # ------------------------------------------------------------------

    def _start_download_ui(self, download_id: str, title: str) -> None:
        card = self._progress.add_download(download_id, title=title)
        card.set_status(DownloadStatus.EXTRACTING)

    def _on_progress(self, download_id: str, progress: DownloadProgress) -> None:
        card = self._progress.get_card(download_id)
        if card:
            card.update_progress(progress)
            card.set_status(DownloadStatus.DOWNLOADING)

    def _update_status(self, download_id: str, status: DownloadStatus) -> None:
        card = self._progress.get_card(download_id)
        if card:
            card.set_status(status)

    def _on_download_complete(
        self, download_id: str, url: str, result: DownloadResult
    ) -> None:
        card = self._progress.get_card(download_id)
        # Use pre-extracted info if available, fall back to result info
        media_info = self._current_info or result.media_info
        if card:
            card.set_status(DownloadStatus.COMPLETED)
            if media_info:
                card.set_title(media_info.title or "Download complete")

        # Add to history
        filepath = result.filepath or (result.files_downloaded[0] if result.files_downloaded else "")
        if filepath:
            entry = HistoryEntry(
                title=media_info.title if media_info else os.path.basename(filepath),
                url=url,
                filepath=filepath,
                media_type=media_info.media_type if media_info else None,
                filesize=media_info.filesize if media_info else None,
            )
            # History panel will be added in a future iteration
            logger.info("Download complete: %s", filepath)

        self._url_input.clear()

    def _on_download_failed(self, download_id: str, error: str) -> None:
        card = self._progress.get_card(download_id)
        if card:
            card.set_status(DownloadStatus.FAILED)
            card.set_title(f"Failed: {error[:80]}")
        logger.error("Download failed: %s", error)
        self._url_input.set_enabled(True)

    # ------------------------------------------------------------------
    # Clipboard monitoring
    # ------------------------------------------------------------------

    def _start_clipboard_monitor(self) -> None:
        """Start watching the clipboard for URLs."""
        self._clipboard_monitor = ClipboardMonitor(
            callback=self._on_clipboard_url,
            interval=1.0,
        )
        if self._settings.get_clipboard_monitoring():
            self._clipboard_monitor.start()

    def _on_clipboard_url(self, url: str) -> None:
        """Called from clipboard monitor thread when a URL is detected."""
        self._root.after(0, self._url_input.set_url, url)

    def _on_settings_changed(self) -> None:
        """React to settings changes."""
        if self._clipboard_monitor:
            if self._settings.get_clipboard_monitoring():
                if not self._clipboard_monitor.is_running:
                    self._clipboard_monitor.start()
            else:
                self._clipboard_monitor.stop()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        """Clean shutdown."""
        if self._clipboard_monitor:
            self._clipboard_monitor.stop()
        self._root.destroy()

    def run(self) -> None:
        """Start the main event loop."""
        logger.info("Opening main window")
        self._root.mainloop()
