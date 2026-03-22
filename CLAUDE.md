# CLAUDE.md — Media Downloader Application

## Project Overview
A local Python desktop application that downloads videos and images from any online source at the **highest available quality** without watermarks. This is a **personal-use tool** — not a web service or SaaS product.

## Tech Stack
- **Language:** Python 3.10+
- **Video Downloads:** `yt-dlp` — supports 1000+ video platforms
- **Image Downloads:** `gallery-dl` — supports 100+ image hosts and social media platforms
- **Media Processing:** FFmpeg (must be installed system-wide) + Pillow for thumbnails
- **GUI Framework:** CustomTkinter (modern-looking Tkinter wrapper, dark mode by default)
- **Testing:** pytest
- **Packaging:** PyInstaller or Nuitka (for `.app` distribution)

## Architecture

### Directory Structure
```
media-downloader/
├── src/
│   ├── main.py              # Entry point
│   ├── app.py               # GUI application bootstrap
│   ├── core/                # Download engine layer
│   │   ├── engine.py        # Abstract DownloadEngine base class
│   │   ├── video_dl.py      # yt-dlp wrapper
│   │   ├── image_dl.py      # gallery-dl wrapper
│   │   ├── url_router.py    # URL detection → engine routing
│   │   ├── quality.py       # Always-highest-quality selection
│   │   └── watermark.py     # Platform-specific watermark avoidance
│   ├── models/              # Data models
│   │   ├── download.py      # Download task state
│   │   └── media_info.py    # Media metadata (title, resolution, etc.)
│   ├── ui/                  # GUI components
│   │   ├── main_window.py   # Main window layout
│   │   ├── url_input.py     # URL input bar + paste button
│   │   ├── preview.py       # Thumbnail + metadata preview
│   │   ├── progress.py      # Download progress bars
│   │   ├── history.py       # Past downloads list
│   │   ├── settings.py      # Output dir, format preferences
│   │   └── styles.py        # Colors, fonts, theme constants
│   └── utils/               # Utility functions
│       ├── ffmpeg.py         # FFmpeg detection
│       ├── clipboard.py     # Clipboard monitoring
│       └── filesystem.py    # Path/file helpers
├── tests/                   # pytest test suite
├── assets/                  # Icons, images
├── downloads/               # Default download output folder
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Project metadata
└── init.sh                  # Dev environment setup script
```

### Core Design Principles
1. **Engine Abstraction** — All download backends implement `DownloadEngine` ABC with `can_handle(url)`, `extract_info(url)`, and `download(url, opts)`. This makes it trivial to add new engines.
2. **URL Router** — Given any URL, the router tries each engine's `can_handle()` and picks the best match. Falls back gracefully.
3. **Always Highest Quality** — Format selection defaults to best available video+audio merge. No user prompt for quality unless they explicitly want lower.
4. **Watermark-Free** — Platform-specific logic in `watermark.py` ensures TikTok, Instagram, etc. serve unwatermarked content.
5. **Async Downloads** — Downloads run in background threads so the GUI never freezes.

## Key Implementation Details

### yt-dlp Options (Video)
```python
YDL_OPTS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
    'merge_output_format': 'mp4',
    'outtmpl': '%(title)s.%(ext)s',
    'noplaylist': False,  # Allow playlist downloads
    'ignoreerrors': True,
    'no_warnings': False,
    'extract_flat': False,
    'writethumbnail': True,
    'postprocessors': [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',
    }],
}
```

### gallery-dl Options (Images)
```python
GDL_OPTS = {
    'directory': ['downloads'],
    'filename': '{filename}.{extension}',
    'skip': True,  # Skip already downloaded
    'image-range': None,  # Download all images
}
```

### URL Routing Logic
```
URL → is it a known video platform?
  YES → yt-dlp
  NO → is it a known image host?
    YES → gallery-dl
    NO → try yt-dlp first (it supports generic extractors)
      FAIL → try gallery-dl
      FAIL → try direct HTTP download
      FAIL → report "unsupported URL"
```

## Coding Conventions
- Use **type hints** everywhere
- Use **dataclasses** or **Pydantic** for models
- Use **logging** module (not print statements)
- Follow **PEP 8**
- Docstrings on all public functions (Google style)
- Tests in `tests/` mirror `src/` structure

## Common Commands
```bash
# Setup
chmod +x init.sh && ./init.sh

# Activate venv
source venv/bin/activate

# Run the app
python -m src.main

# Run tests
python -m pytest tests/ -v

# Run a quick download test
python -c "from src.core.video_dl import VideoDownloader; VideoDownloader().download('https://example.com/video')"
```

## Platform-Specific Notes

### TikTok (watermark-free)
yt-dlp automatically selects the watermark-free stream when available. The `watermark.py` module adds additional logic for edge cases.

### Instagram
Requires cookies/authentication for private content. Public posts download at original quality without watermarks. Use `gallery-dl` with cookie file for authenticated downloads.

### Twitter/X
yt-dlp handles video. gallery-dl handles images. Both support tweet URLs directly. For highest quality images, append `:orig` to the image URL pattern.

### YouTube
yt-dlp handles everything. For 4K+/8K, FFmpeg MUST be installed to merge separate video+audio streams.

## Status
🟢 **Phase:** Execution — building core engine and GUI with Claude Code Opus 4.6

## Decided Defaults
- **GUI:** CustomTkinter (dark mode by default)
- **Priority platforms:** YouTube, TikTok, Instagram, Twitter/X, Reddit, Pinterest, Imgur + all yt-dlp/gallery-dl supported sites
- **Clipboard monitoring:** Enabled (toggleable in settings)
- **Batch downloads:** Supported (multiple URLs, playlists, albums)
- **Video output:** MP4 (H.264+AAC merge via FFmpeg)
- **Image output:** Keep original format
- **Download location:** `~/Downloads/MediaDownloader/`
- **Theme:** Dark mode default, light mode toggle available
- **Packaging:** PyInstaller for `.app` bundle
