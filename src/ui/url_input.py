"""URL input bar with paste and download buttons."""

import logging
from typing import Callable, Optional

import customtkinter as ctk

from src.ui.styles import (
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_BG_CARD,
    COLOR_BG_ELEVATED,
    COLOR_BG_INPUT,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    CORNER_RADIUS,
    CORNER_RADIUS_SM,
    FONT_BODY,
    FONT_BUTTON,
    FONT_MONO_SM,
    INPUT_HEIGHT,
    PAD_MD,
    PAD_SM,
)
from src.utils.clipboard import read_clipboard, is_url

logger = logging.getLogger(__name__)


class URLInputBar(ctk.CTkFrame):
    """URL input bar with paste button and download trigger."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_submit: Callable[[str], None],
        on_url_changed: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLOR_BG_CARD,
            corner_radius=CORNER_RADIUS,
            border_width=0,
            **kwargs,
        )
        self._on_submit = on_submit
        self._on_url_changed = on_url_changed
        self._debounce_id: Optional[str] = None
        self._last_notified_url: str = ""
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        # Paste button — ghost style
        self._paste_btn = ctk.CTkButton(
            self,
            text="\u2398   PASTE",
            width=88,
            height=INPUT_HEIGHT,
            font=FONT_MONO_SM,
            fg_color="transparent",
            border_width=0,
            hover_color=COLOR_BG_ELEVATED,
            text_color=COLOR_TEXT_DIM,
            corner_radius=CORNER_RADIUS_SM,
            command=self._paste_from_clipboard,
        )
        self._paste_btn.grid(row=0, column=0, padx=(PAD_SM, 0), pady=PAD_SM)

        # URL entry — large and prominent
        self._entry = ctk.CTkEntry(
            self,
            height=INPUT_HEIGHT,
            font=FONT_BODY,
            fg_color=COLOR_BG_INPUT,
            border_width=0,
            text_color=COLOR_TEXT,
            placeholder_text="paste any URL \u2014 video, image, gallery, anything...",
            placeholder_text_color=COLOR_TEXT_DIM,
            corner_radius=CORNER_RADIUS_SM,
        )
        self._entry.grid(row=0, column=1, padx=PAD_SM, pady=PAD_SM, sticky="ew")
        self._entry.bind("<Return>", lambda _: self._submit())
        self._entry.bind("<KeyRelease>", lambda _: self._on_text_changed())
        self._entry.bind("<<Paste>>", lambda _: self.after(50, self._on_text_changed))

        # Download button — teal accent, black text
        self._dl_btn = ctk.CTkButton(
            self,
            text="\u2193   SNAG",
            width=130,
            height=INPUT_HEIGHT,
            font=FONT_BUTTON,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#0B0C12",
            corner_radius=CORNER_RADIUS_SM,
            command=self._submit,
        )
        self._dl_btn.grid(row=0, column=2, padx=(0, PAD_SM), pady=PAD_SM)

    def _paste_from_clipboard(self) -> None:
        """Paste clipboard content into the entry field."""
        content = read_clipboard()
        if content:
            self._entry.delete(0, "end")
            self._entry.insert(0, content.strip())
            self._on_text_changed()

    def _submit(self) -> None:
        """Submit the current URL after basic validation."""
        url = self._entry.get().strip()
        if url and (url.startswith("http://") or url.startswith("https://")):
            logger.info("URL submitted: %s", url)
            self._on_submit(url)

    def _on_text_changed(self) -> None:
        """Debounce URL change notifications (500ms after last change)."""
        if not self._on_url_changed:
            return
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(500, self._notify_url_changed)

    def _notify_url_changed(self) -> None:
        """Fire the URL changed callback if the URL is valid and new."""
        self._debounce_id = None
        url = self._entry.get().strip()
        if url and url != self._last_notified_url and (url.startswith("http://") or url.startswith("https://")):
            self._last_notified_url = url
            self._on_url_changed(url)

    def clear(self) -> None:
        """Clear the input field."""
        self._entry.delete(0, "end")

    def set_url(self, url: str) -> None:
        """Set a URL in the input field."""
        self._entry.delete(0, "end")
        self._entry.insert(0, url)
        self._on_text_changed()

    def get_url(self) -> str:
        """Get the current URL text."""
        return self._entry.get().strip()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the input bar."""
        state = "normal" if enabled else "disabled"
        self._entry.configure(state=state)
        self._dl_btn.configure(state=state)
        self._paste_btn.configure(state=state)
