# Snag

A desktop application that downloads videos and images from the web at the highest available quality, without watermarks.

Snag wraps [yt-dlp](https://github.com/yt-dlp/yt-dlp) (1000+ video sites) and [gallery-dl](https://github.com/mikf/gallery-dl) (100+ image hosts) behind a clean, dark-mode GUI built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).

## Features

- **Paste any URL** — YouTube, TikTok, Instagram, Twitter/X, Reddit, Imgur, Pinterest, Flickr, and hundreds more
- **Highest quality by default** — always selects the best available resolution and bitrate
- **Watermark-free** — platform-specific logic ensures clean downloads from TikTok, Instagram, etc.
- **Live preview** — see thumbnail, title, uploader, resolution, and file size before downloading
- **Clipboard monitoring** — automatically detects URLs copied to your clipboard
- **Batch support** — playlists, albums, and galleries download in full
- **MP4 output** — video+audio merged via FFmpeg into universally playable H.264 MP4

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on your PATH (required for merging video+audio streams)

## Setup

```bash
# Clone the repo
git clone https://github.com/Cbojan22/snag.git
cd snag

# Run the setup script (creates venv, installs dependencies)
chmod +x init.sh && ./init.sh

# Or set up manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
source venv/bin/activate
python -m src.main
```

1. Paste or type a URL into the input bar
2. Preview appears automatically (thumbnail, title, platform info)
3. Click **Download** — file saves to `~/Downloads/Snag/`

## Configuration

Settings are available in the bottom bar of the app:

- **Download directory** — change where files are saved
- **Prefer MP4** — toggle H.264 MP4 output (on by default)
- **Clipboard monitoring** — auto-detect URLs from clipboard (on by default)

## Supported Platforms

**Video** (via yt-dlp): YouTube, TikTok, Twitter/X, Vimeo, Reddit, Twitch, Dailymotion, and [1000+ more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

**Images** (via gallery-dl): Imgur, Flickr, DeviantArt, ArtStation, Pixiv, Pinterest, Unsplash, Instagram, Twitter/X images, Reddit images, and [100+ more](https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md)

## Project Structure

```
snag/
├── src/
│   ├── main.py              # Entry point
│   ├── core/                # Download engines
│   │   ├── engine.py        # Abstract base class + data models
│   │   ├── video_dl.py      # yt-dlp wrapper
│   │   ├── image_dl.py      # gallery-dl wrapper
│   │   ├── url_router.py    # URL → engine routing
│   │   └── watermark.py     # Watermark-free download logic
│   ├── ui/                  # GUI components
│   │   ├── main_window.py   # Main window layout
│   │   ├── url_input.py     # URL input bar
│   │   ├── preview.py       # Thumbnail + metadata preview
│   │   ├── progress.py      # Download progress cards
│   │   ├── settings.py      # Settings panel
│   │   └── styles.py        # Theme constants
│   └── utils/               # Helpers
│       ├── clipboard.py     # Clipboard monitoring
│       ├── ffmpeg.py        # FFmpeg detection
│       └── filesystem.py    # File/path utilities
├── assets/                  # App icon
├── tests/                   # Test suite
├── requirements.txt
└── pyproject.toml
```

## License

For personal use.
