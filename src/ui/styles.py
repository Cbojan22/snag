"""Theme constants — Soft Midnight."""

# Window
WINDOW_TITLE = "Snag"
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 680
WINDOW_DEFAULT_SIZE = "1060x740"

# Fonts
FONT_DISPLAY = ("SF Pro Display", "Segoe UI", "Helvetica")
FONT_TEXT = ("SF Pro Text", "Segoe UI", "Helvetica")
FONT_CODE = ("SF Mono", "Cascadia Code", "JetBrains Mono", "Menlo", "Consolas")

FONT_LOGO = ("DIN Condensed", 132, "bold")
FONT_HEADING = (FONT_DISPLAY[0], 26, "bold")
FONT_SUBHEADING = (FONT_DISPLAY[0], 15, "bold")
FONT_BODY = (FONT_TEXT[0], 13)
FONT_SMALL = (FONT_TEXT[0], 11)
FONT_TINY = (FONT_TEXT[0], 10)
FONT_BUTTON = (FONT_TEXT[0], 13, "bold")
FONT_MONO = (FONT_CODE[0], 11)
FONT_MONO_SM = (FONT_CODE[0], 10)

# ── Colors ────────────────────────────────────────────────────────
# Soft midnight backgrounds — warm, not pure black
COLOR_BG = "#1e1e2e"
COLOR_BG_SECONDARY = "#181825"
COLOR_BG_CARD = "#262637"
COLOR_BG_CARD_HOVER = "#2e2e42"
COLOR_BG_INPUT = "#1a1a28"
COLOR_BG_ELEVATED = "#313244"

# Teal accent — refreshing, easy on the eyes
COLOR_ACCENT = "#94e2d5"
COLOR_ACCENT_HOVER = "#a6f0e4"
COLOR_ACCENT_DIM = "#3b6e64"
COLOR_ACCENT_GLOW = "#94e2d5"

# Status
COLOR_SUCCESS = "#a6e3a1"
COLOR_SUCCESS_DIM = "#40634e"
COLOR_WARNING = "#f9e2af"
COLOR_ERROR = "#f38ba8"
COLOR_ERROR_DIM = "#6e3545"

# Text — warm off-white, never pure white
COLOR_TEXT = "#cdd6f4"
COLOR_TEXT_SECONDARY = "#a6adc8"
COLOR_TEXT_DIM = "#6c7086"
COLOR_TEXT_MUTED = "#45475a"

# Borders & dividers
COLOR_BORDER = "#313244"
COLOR_BORDER_SUBTLE = "#2a2a3c"
COLOR_BORDER_ACCENT = "#3b6e64"

# ── Spacing ───────────────────────────────────────────────────────
PAD_XS = 4
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24
PAD_XL = 32
PAD_2XL = 40

# ── Radii ─────────────────────────────────────────────────────────
CORNER_RADIUS = 12
CORNER_RADIUS_SM = 8
CORNER_RADIUS_LG = 16
CORNER_RADIUS_PILL = 50

# ── Progress ──────────────────────────────────────────────────────
PROGRESS_HEIGHT = 6
PROGRESS_COLOR = COLOR_ACCENT
PROGRESS_BG = COLOR_BG_INPUT

# ── Component sizes ──────────────────────────────────────────────
INPUT_HEIGHT = 48
BUTTON_HEIGHT = 48
BUTTON_SM_HEIGHT = 34
THUMB_WIDTH = 280
THUMB_HEIGHT = 158
