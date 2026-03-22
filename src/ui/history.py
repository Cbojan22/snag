"""Past downloads history list."""

import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from src.core.engine import MediaType
from src.ui.styles import (
    COLOR_ACCENT,
    COLOR_BG_CARD,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TEXT_SECONDARY,
    CORNER_RADIUS,
    CORNER_RADIUS_SM,
    FONT_BODY,
    FONT_SMALL,
    PAD_MD,
    PAD_SM,
)
from src.utils.filesystem import format_filesize

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """A completed download entry."""

    title: str
    url: str
    filepath: str
    media_type: MediaType
    filesize: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)


class HistoryItem(ctk.CTkFrame):
    """A single history row."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        entry: HistoryEntry,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLOR_BG_CARD,
            corner_radius=CORNER_RADIUS_SM,
            height=48,
            **kwargs,
        )
        self._entry = entry
        self.grid_columnconfigure(1, weight=1)

        # Type icon
        icon = "\U0001f3ac" if entry.media_type == MediaType.VIDEO else "\U0001f5bc"
        icon_label = ctk.CTkLabel(
            self, text=icon, font=FONT_BODY, width=30
        )
        icon_label.grid(row=0, column=0, padx=(PAD_SM, 4), pady=PAD_SM)

        # Title
        title_label = ctk.CTkLabel(
            self,
            text=entry.title or "Untitled",
            font=FONT_BODY,
            text_color=COLOR_TEXT,
            anchor="w",
        )
        title_label.grid(row=0, column=1, padx=0, pady=PAD_SM, sticky="w")

        # Size + time
        details: list[str] = []
        if entry.filesize:
            details.append(format_filesize(entry.filesize))
        details.append(entry.timestamp.strftime("%H:%M"))
        detail_label = ctk.CTkLabel(
            self,
            text="  \u2022  ".join(details),
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
            anchor="e",
        )
        detail_label.grid(row=0, column=2, padx=PAD_SM, pady=PAD_SM, sticky="e")

        # Open file button
        open_btn = ctk.CTkButton(
            self,
            text="Open",
            width=55,
            height=28,
            font=FONT_SMALL,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_BG_INPUT,
            text_color=COLOR_TEXT_SECONDARY,
            corner_radius=CORNER_RADIUS_SM,
            command=self._open_file,
        )
        open_btn.grid(row=0, column=3, padx=(4, PAD_SM), pady=PAD_SM)

    def _open_file(self) -> None:
        """Open the downloaded file with the default system application."""
        path = self._entry.filepath
        if not os.path.exists(path):
            logger.warning("File not found: %s", path)
            return
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
            elif sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            logger.exception("Failed to open file: %s", path)


class HistoryPanel(ctk.CTkScrollableFrame):
    """Scrollable list of past downloads."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs) -> None:
        super().__init__(
            master,
            fg_color="transparent",
            corner_radius=0,
            label_text="Recent Downloads",
            label_font=FONT_BODY,
            label_text_color=COLOR_TEXT_SECONDARY,
            **kwargs,
        )
        self._entries: list[HistoryEntry] = []
        self._items: list[HistoryItem] = []
        self.grid_columnconfigure(0, weight=1)

        # Empty state
        self._empty_label = ctk.CTkLabel(
            self,
            text="No downloads yet",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
        )
        self._empty_label.grid(row=0, column=0, pady=PAD_MD)

    def add_entry(self, entry: HistoryEntry) -> None:
        """Add a download to the history."""
        self._entries.insert(0, entry)
        self._empty_label.grid_remove()

        item = HistoryItem(self, entry)
        # Shift existing items down
        for i, existing in enumerate(self._items):
            existing.grid(row=i + 1, column=0, padx=0, pady=(0, 4), sticky="ew")
        item.grid(row=0, column=0, padx=0, pady=(0, 4), sticky="ew")
        self._items.insert(0, item)

        # Keep max 50 items
        while len(self._items) > 50:
            old = self._items.pop()
            old.destroy()
            self._entries.pop()

    def clear(self) -> None:
        """Clear all history."""
        for item in self._items:
            item.destroy()
        self._items.clear()
        self._entries.clear()
        self._empty_label.grid()
