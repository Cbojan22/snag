"""Settings panel for output directory, format preferences, and toggles."""

import logging
from typing import Callable, Optional

import customtkinter as ctk

from src.ui.styles import (
    BUTTON_SM_HEIGHT,
    COLOR_ACCENT,
    COLOR_ACCENT_DIM,
    COLOR_BG_CARD,
    COLOR_BG_ELEVATED,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_BORDER_SUBTLE,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    CORNER_RADIUS,
    CORNER_RADIUS_SM,
    FONT_BODY,
    FONT_MONO_SM,
    FONT_SMALL,
    FONT_TINY,
    PAD_MD,
    PAD_SM,
    PAD_XS,
)
from src.utils.filesystem import DEFAULT_DOWNLOAD_DIR

logger = logging.getLogger(__name__)


class SettingsPanel(ctk.CTkFrame):
    """Collapsible settings panel."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_settings_changed: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLOR_BG_CARD,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=COLOR_BORDER,
            **kwargs,
        )
        self._on_changed = on_settings_changed
        self._expanded = False
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Toggle header — minimal
        self._toggle_btn = ctk.CTkButton(
            self,
            text="\u2699  Settings",
            font=FONT_SMALL,
            fg_color="transparent",
            hover_color=COLOR_BG_ELEVATED,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            height=36,
            command=self._toggle,
        )
        self._toggle_btn.grid(row=0, column=0, padx=PAD_SM, pady=PAD_XS, sticky="ew")

        # Content frame (hidden by default)
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid_columnconfigure(1, weight=1)

        # --- Output directory ---
        ctk.CTkLabel(
            self._content,
            text="Output",
            font=FONT_TINY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, padx=(PAD_MD, PAD_SM), pady=(PAD_MD, PAD_XS), sticky="w")

        self._dir_entry = ctk.CTkEntry(
            self._content,
            height=BUTTON_SM_HEIGHT,
            font=FONT_MONO_SM,
            fg_color=COLOR_BG_INPUT,
            border_width=1,
            border_color=COLOR_BORDER_SUBTLE,
            text_color=COLOR_TEXT_SECONDARY,
            corner_radius=CORNER_RADIUS_SM,
        )
        self._dir_entry.grid(row=0, column=1, padx=0, pady=(PAD_MD, PAD_XS), sticky="ew")
        self._dir_entry.insert(0, str(DEFAULT_DOWNLOAD_DIR))

        browse_btn = ctk.CTkButton(
            self._content,
            text="Browse",
            width=65,
            height=BUTTON_SM_HEIGHT,
            font=FONT_TINY,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            hover_color=COLOR_BG_ELEVATED,
            text_color=COLOR_TEXT_DIM,
            corner_radius=CORNER_RADIUS_SM,
            command=self._browse_dir,
        )
        browse_btn.grid(row=0, column=2, padx=(PAD_SM, PAD_MD), pady=(PAD_MD, PAD_XS))

        # --- Clipboard monitoring toggle ---
        self._clipboard_var = ctk.BooleanVar(value=True)
        self._clipboard_toggle = ctk.CTkSwitch(
            self._content,
            text="Monitor clipboard for URLs",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
            variable=self._clipboard_var,
            onvalue=True,
            offvalue=False,
            command=self._on_setting_changed,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_TEXT_SECONDARY,
            button_hover_color=COLOR_TEXT,
        )
        self._clipboard_toggle.grid(
            row=1, column=0, columnspan=3, padx=PAD_MD, pady=(PAD_SM, PAD_XS), sticky="w"
        )

        # --- Prefer MP4 toggle ---
        self._mp4_var = ctk.BooleanVar(value=True)
        self._mp4_toggle = ctk.CTkSwitch(
            self._content,
            text="Prefer MP4 format for videos",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_DIM,
            variable=self._mp4_var,
            onvalue=True,
            offvalue=False,
            command=self._on_setting_changed,
            progress_color=COLOR_ACCENT,
            button_color=COLOR_TEXT_SECONDARY,
            button_hover_color=COLOR_TEXT,
        )
        self._mp4_toggle.grid(
            row=2, column=0, columnspan=3, padx=PAD_MD, pady=(PAD_XS, PAD_MD), sticky="w"
        )

    def _toggle(self) -> None:
        """Expand or collapse settings."""
        self._expanded = not self._expanded
        if self._expanded:
            self._toggle_btn.configure(text="\u2699  Settings  \u25B4")
            self._content.grid(row=1, column=0, padx=0, pady=(0, PAD_SM), sticky="ew")
        else:
            self._toggle_btn.configure(text="\u2699  Settings")
            self._content.grid_remove()

    def _browse_dir(self) -> None:
        """Open a folder picker dialog."""
        path = ctk.filedialog.askdirectory(
            initialdir=self.get_download_dir(),
            title="Select Download Folder",
        )
        if path:
            self._dir_entry.delete(0, "end")
            self._dir_entry.insert(0, path)
            self._on_setting_changed()

    def _on_setting_changed(self) -> None:
        if self._on_changed:
            self._on_changed()

    # --- Public getters ---

    def get_download_dir(self) -> str:
        """Get the configured download directory."""
        return self._dir_entry.get().strip() or str(DEFAULT_DOWNLOAD_DIR)

    def get_clipboard_monitoring(self) -> bool:
        """Whether clipboard monitoring is enabled."""
        return self._clipboard_var.get()

    def get_prefer_mp4(self) -> bool:
        """Whether to prefer MP4 output."""
        return self._mp4_var.get()
