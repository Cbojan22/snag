"""Thumbnail and metadata preview panel."""

import io
import logging
from typing import Optional

import customtkinter as ctk
from PIL import Image

from src.core.engine import MediaInfo, MediaType
from src.ui.styles import (
    COLOR_ACCENT,
    COLOR_BG_CARD,
    COLOR_BG_ELEVATED,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_HIGHLIGHT,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    CORNER_RADIUS,
    CORNER_RADIUS_SM,
    FONT_BODY,
    FONT_MONO_SM,
    FONT_MONO_TAG,
    FONT_SMALL,
    FONT_SUBHEADING,
    FONT_TINY,
    PAD_MD,
    PAD_SM,
    PAD_XS,
    THUMB_HEIGHT,
    THUMB_WIDTH,
)
from src.utils.filesystem import format_duration, format_filesize

logger = logging.getLogger(__name__)


class PreviewPanel(ctk.CTkFrame):
    """Shows thumbnail and metadata for a detected URL."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=COLOR_BG_CARD,
            corner_radius=CORNER_RADIUS,
            border_width=0,
            **kwargs,
        )
        self._thumb_image: Optional[ctk.CTkImage] = None
        self._build()
        self.clear()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # ── Top banner: platform · type · resolution · duration · size ──
        self._banner = ctk.CTkFrame(self, fg_color=COLOR_BG_ELEVATED, corner_radius=0)
        self._banner.grid(row=0, column=0, sticky="ew")
        self._banner.grid_columnconfigure(1, weight=1)

        self._platform_label = ctk.CTkLabel(
            self._banner,
            text="",
            font=FONT_MONO_TAG,
            text_color=COLOR_ACCENT,
            anchor="w",
        )
        self._platform_label.grid(
            row=0, column=0, padx=(PAD_MD, PAD_SM), pady=PAD_XS, sticky="w"
        )

        self._info_label = ctk.CTkLabel(
            self._banner,
            text="",
            font=FONT_MONO_SM,
            text_color=COLOR_TEXT_DIM,
            anchor="w",
        )
        self._info_label.grid(
            row=0, column=1, padx=0, pady=PAD_XS, sticky="w"
        )

        self._uploader_label = ctk.CTkLabel(
            self._banner,
            text="",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_SECONDARY,
            anchor="e",
        )
        self._uploader_label.grid(
            row=0, column=2, padx=(PAD_SM, PAD_MD), pady=PAD_XS, sticky="e"
        )

        # ── Content row: thumbnail + title ──
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=1, column=0, sticky="ew", padx=PAD_MD, pady=PAD_MD)
        self._content.grid_columnconfigure(1, weight=1)

        # Thumbnail
        self._thumb_label = ctk.CTkLabel(
            self._content,
            text="",
            width=THUMB_WIDTH,
            height=THUMB_HEIGHT,
            fg_color=COLOR_BG_INPUT,
            corner_radius=CORNER_RADIUS_SM,
        )
        self._thumb_label.grid(
            row=0, column=0, padx=(0, PAD_MD), pady=0, sticky="nw"
        )

        # Title — large, wraps to fill available space
        self._title_label = ctk.CTkLabel(
            self._content,
            text="",
            font=FONT_SUBHEADING,
            text_color=COLOR_TEXT,
            anchor="nw",
            justify="left",
            wraplength=550,
        )
        self._title_label.grid(
            row=0, column=1, padx=0, pady=0, sticky="nw"
        )

    def update_info(self, info: MediaInfo) -> None:
        """Update the preview with media info."""
        self._title_label.configure(text=info.title or "Untitled")
        self._uploader_label.configure(text=info.uploader or "")

        # Build info string — resolution · duration · size
        parts: list[str] = []
        if info.resolution and info.resolution != "Unknown":
            parts.append(info.resolution)
        if info.duration:
            parts.append(format_duration(info.duration))
        if info.filesize:
            parts.append(format_filesize(info.filesize))
        self._info_label.configure(text="  \u00b7  ".join(parts))

        # Platform · type badge
        type_str = info.media_type.name.capitalize() if info.media_type else ""
        platform = info.source_site.upper() if info.source_site else ""
        label = f"{platform}  \u00b7  {type_str}" if platform and type_str else platform or type_str
        self._platform_label.configure(text=label)

        self.grid()  # show panel

    def set_thumbnail_from_bytes(self, data: bytes) -> None:
        """Set thumbnail from raw image bytes."""
        try:
            pil_img = Image.open(io.BytesIO(data))
            pil_img.thumbnail((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
            self._thumb_image = ctk.CTkImage(
                light_image=pil_img,
                dark_image=pil_img,
                size=(THUMB_WIDTH, THUMB_HEIGHT),
            )
            self._thumb_label.configure(image=self._thumb_image, text="")
        except Exception:
            logger.warning("Failed to load thumbnail image")

    def set_unavailable(self) -> None:
        """Show 'preview not available' state."""
        self._platform_label.configure(text="")
        self._info_label.configure(text="")
        self._uploader_label.configure(text="")
        self._title_label.configure(text="Preview not available")
        self._thumb_label.configure(image=None, text="")
        self.grid()

    def set_loading(self) -> None:
        """Show loading state."""
        self._platform_label.configure(text="")
        self._info_label.configure(text="")
        self._uploader_label.configure(text="")
        self._title_label.configure(text="Fetching info...")
        self._thumb_label.configure(image=None, text="")
        self.grid()

    def clear(self) -> None:
        """Hide / reset the preview panel."""
        self._platform_label.configure(text="")
        self._info_label.configure(text="")
        self._uploader_label.configure(text="")
        self._title_label.configure(text="")
        self._thumb_label.configure(image=None, text="")
        self._thumb_image = None
        self.grid_remove()  # hide until needed
