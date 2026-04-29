"""Theme constants — Voltage.

Acid lime on deep blue-black with warm coral highlights. Designed to feel
fast, fresh, and a little electric — opposite of the cool teal that every
other downloader uses.
"""

# ── Window ────────────────────────────────────────────────────────
WINDOW_TITLE = "Snag"
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 780
WINDOW_DEFAULT_SIZE = "1060x860"

# ── Fonts ─────────────────────────────────────────────────────────
# Tkinter only respects the first family name in each tuple; the rest
# are documentation for cross-platform intent.
FONT_DISPLAY = ("SF Pro Display", "Helvetica Neue", "Helvetica")
FONT_TEXT = ("SF Pro Text", "Helvetica Neue", "Helvetica")
FONT_CODE = ("JetBrains Mono", "SF Mono", "Menlo", "Consolas")
FONT_GEOMETRIC = ("Futura", "SF Pro Display", "Helvetica Neue")  # Logo wordmark

FONT_LOGO = (FONT_GEOMETRIC[0], 88, "bold")
FONT_LOGO_GLYPH = (FONT_GEOMETRIC[0], 28, "bold")
FONT_HEADING = (FONT_DISPLAY[0], 24, "bold")
FONT_SUBHEADING = (FONT_DISPLAY[0], 15, "bold")
FONT_BODY = (FONT_TEXT[0], 13)
FONT_BODY_BOLD = (FONT_TEXT[0], 13, "bold")
FONT_SMALL = (FONT_TEXT[0], 11)
FONT_TINY = (FONT_TEXT[0], 10)
FONT_BUTTON = (FONT_TEXT[0], 13, "bold")
FONT_MONO = (FONT_CODE[0], 11)
FONT_MONO_SM = (FONT_CODE[0], 10)
FONT_MONO_TAG = (FONT_CODE[0], 10, "bold")

# ── Colors — Voltage ──────────────────────────────────────────────
# Deep blue-black backgrounds — slightly cool, never pure black.
COLOR_BG = "#0B0C12"
COLOR_BG_SECONDARY = "#0F1118"
COLOR_BG_CARD = "#15171F"
COLOR_BG_CARD_HOVER = "#1B1D26"
COLOR_BG_INPUT = "#0F1018"
COLOR_BG_ELEVATED = "#1F2129"

# Acid lime — the brand punch. Fresh, electric, alive.
COLOR_ACCENT = "#C8F23F"
COLOR_ACCENT_HOVER = "#D7FF63"
COLOR_ACCENT_DIM = "#5C6E1F"
COLOR_ACCENT_GLOW = "#C8F23F"

# Coral — warm secondary, used for active/highlight states
COLOR_HIGHLIGHT = "#FF7457"
COLOR_HIGHLIGHT_DIM = "#6E3327"

# Status
COLOR_SUCCESS = "#A8E66E"
COLOR_SUCCESS_DIM = "#3F5C2A"
COLOR_WARNING = "#FFCB57"
COLOR_ERROR = "#FF5C6D"
COLOR_ERROR_DIM = "#6E2A33"

# Text — soft white with cool undertone, never pure white
COLOR_TEXT = "#EBECF2"
COLOR_TEXT_SECONDARY = "#9D9FAB"
COLOR_TEXT_DIM = "#5F616E"
COLOR_TEXT_MUTED = "#3A3C46"

# Borders & dividers
COLOR_BORDER = "#23252E"
COLOR_BORDER_SUBTLE = "#1A1C24"
COLOR_BORDER_ACCENT = "#5C6E1F"

# ── Spacing ───────────────────────────────────────────────────────
PAD_XS = 4
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24
PAD_XL = 32
PAD_2XL = 40

# ── Radii ─────────────────────────────────────────────────────────
CORNER_RADIUS = 14
CORNER_RADIUS_SM = 10
CORNER_RADIUS_LG = 18
CORNER_RADIUS_PILL = 50

# ── Progress ──────────────────────────────────────────────────────
PROGRESS_HEIGHT = 4
PROGRESS_COLOR = COLOR_ACCENT
PROGRESS_BG = COLOR_BG_INPUT

# ── Component sizes ──────────────────────────────────────────────
INPUT_HEIGHT = 50
BUTTON_HEIGHT = 50
BUTTON_SM_HEIGHT = 34
THUMB_WIDTH = 280
THUMB_HEIGHT = 158
