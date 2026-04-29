"""Download progress bars and status display."""

import logging
from typing import Optional

import customtkinter as ctk

from src.core.engine import DownloadProgress, DownloadStatus
from src.ui.styles import (
    COLOR_ACCENT,
    COLOR_ACCENT_DIM,
    COLOR_BG_CARD,
    COLOR_BG_ELEVATED,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_BORDER_SUBTLE,
    COLOR_ERROR,
    COLOR_ERROR_DIM,
    COLOR_HIGHLIGHT,
    COLOR_SUCCESS,
    COLOR_SUCCESS_DIM,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    CORNER_RADIUS,
    CORNER_RADIUS_SM,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO_SM,
    FONT_MONO_TAG,
    FONT_SMALL,
    FONT_TINY,
    PAD_MD,
    PAD_SM,
    PAD_XS,
    PROGRESS_COLOR,
    PROGRESS_HEIGHT,
)

logger = logging.getLogger(__name__)


class DownloadProgressCard(ctk.CTkFrame):
    """A single download progress card with title, bar, and speed/ETA."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str = "Downloading...",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLOR_BG_CARD,
            corner_radius=CORNER_RADIUS,
            border_width=0,
            **kwargs,
        )
        self._title = title
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Title row
        self._title_label = ctk.CTkLabel(
            self,
            text=self._title,
            font=FONT_BODY,
            text_color=COLOR_TEXT,
            anchor="w",
        )
        self._title_label.grid(
            row=0, column=0, padx=PAD_MD, pady=(PAD_MD, PAD_XS), sticky="ew"
        )

        # Status badge (right-aligned)
        self._status_label = ctk.CTkLabel(
            self,
            text="PENDING",
            font=FONT_MONO_TAG,
            text_color=COLOR_TEXT_MUTED,
            anchor="e",
        )
        self._status_label.grid(
            row=0, column=1, padx=PAD_MD, pady=(PAD_MD, PAD_XS), sticky="e"
        )

        # Thin progress bar
        self._progress_bar = ctk.CTkProgressBar(
            self,
            height=PROGRESS_HEIGHT,
            corner_radius=3,
            fg_color=COLOR_BG_INPUT,
            progress_color=PROGRESS_COLOR,
        )
        self._progress_bar.grid(
            row=1, column=0, columnspan=2, padx=PAD_MD, pady=(PAD_SM, PAD_XS), sticky="ew"
        )
        self._progress_bar.set(0)

        # Detail row — monospace for stats
        self._detail_label = ctk.CTkLabel(
            self,
            text="",
            font=FONT_MONO_SM,
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        )
        self._detail_label.grid(
            row=2, column=0, columnspan=2, padx=PAD_MD, pady=(0, PAD_MD), sticky="ew"
        )

    def update_progress(self, progress: DownloadProgress) -> None:
        """Update the progress display."""
        if progress.percent is not None:
            self._progress_bar.set(progress.percent / 100.0)

        parts: list[str] = []
        if progress.percent is not None:
            parts.append(f"{progress.percent:.1f}%")
        if progress.speed_human:
            parts.append(progress.speed_human)
        if progress.eta:
            eta_min, eta_sec = divmod(int(progress.eta), 60)
            if eta_min:
                parts.append(f"ETA {eta_min}m {eta_sec}s")
            else:
                parts.append(f"ETA {eta_sec}s")
        self._detail_label.configure(text="  \u00b7  ".join(parts))

    def set_status(self, status: DownloadStatus) -> None:
        """Update the status label and color."""
        label_map = {
            DownloadStatus.PENDING: ("PENDING", COLOR_TEXT_MUTED),
            DownloadStatus.EXTRACTING: ("EXTRACTING", COLOR_TEXT_SECONDARY),
            DownloadStatus.DOWNLOADING: ("DOWNLOADING", COLOR_ACCENT),
            DownloadStatus.PROCESSING: ("PROCESSING", COLOR_ACCENT),
            DownloadStatus.COMPLETED: ("\u2713 DONE", COLOR_SUCCESS),
            DownloadStatus.FAILED: ("\u2717 FAILED", COLOR_ERROR),
            DownloadStatus.CANCELLED: ("CANCELLED", COLOR_TEXT_DIM),
        }
        text, color = label_map.get(status, ("UNKNOWN", COLOR_TEXT_DIM))
        self._status_label.configure(text=text, text_color=color)

        if status == DownloadStatus.COMPLETED:
            self._progress_bar.configure(progress_color=COLOR_SUCCESS)
            self._progress_bar.set(1.0)
        elif status == DownloadStatus.FAILED:
            self._progress_bar.configure(progress_color=COLOR_ERROR)
        elif status == DownloadStatus.DOWNLOADING:
            self._progress_bar.configure(progress_color=COLOR_ACCENT)

    def set_title(self, title: str) -> None:
        """Update the title."""
        self._title_label.configure(text=title)


class ProgressPanel(ctk.CTkScrollableFrame):
    """Scrollable panel showing all active/recent download progress cards."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs) -> None:
        super().__init__(
            master,
            fg_color="transparent",
            corner_radius=0,
            **kwargs,
        )
        self._cards: dict[str, DownloadProgressCard] = {}
        self.grid_columnconfigure(0, weight=1)
        self._row = 0

        # Empty state label
        self._empty_label = ctk.CTkLabel(
            self,
            text="nothing snagged yet\npaste a URL above to begin",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            justify="center",
        )
        self._empty_label.grid(row=0, column=0, pady=PAD_MD * 4)

    def add_download(self, download_id: str, title: str = "Downloading...") -> DownloadProgressCard:
        """Add a new download progress card and return it."""
        # Hide empty state
        self._empty_label.grid_remove()

        card = DownloadProgressCard(self, title=title)
        card.grid(row=self._row, column=0, padx=0, pady=(0, PAD_SM), sticky="ew")
        self._cards[download_id] = card
        self._row += 1
        return card

    def get_card(self, download_id: str) -> Optional[DownloadProgressCard]:
        """Get a progress card by download ID."""
        return self._cards.get(download_id)

    def remove_download(self, download_id: str) -> None:
        """Remove a download card."""
        card = self._cards.pop(download_id, None)
        if card:
            card.destroy()
        if not self._cards:
            self._empty_label.grid()

    def clear_completed(self) -> None:
        """Remove all completed download cards."""
        to_remove = [
            did for did, card in self._cards.items()
            if card._status_label.cget("text") == "\u2713 DONE"
        ]
        for did in to_remove:
            self.remove_download(did)
