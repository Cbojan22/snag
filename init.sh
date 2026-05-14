#!/bin/bash
# ============================================================
# Snag — Project Init Script
# ============================================================
# This script sets up the development environment for the
# Snag application. Run once to get started.
# Usage: chmod +x init.sh && ./init.sh
# ============================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║                Snag — Project Setup                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ----------------------------------------------------------
# 1. Check Python version
# ----------------------------------------------------------
echo -e "${BLUE}[1/6]${NC} Checking Python version..."

if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        echo -e "  ${GREEN}✓${NC} Python $PY_VERSION detected (3.10+ required)"
    else
        echo -e "  ${RED}✗${NC} Python $PY_VERSION detected but 3.10+ is required"
        echo -e "  ${YELLOW}→ Install Python 3.10+: https://www.python.org/downloads/${NC}"
        exit 1
    fi
else
    echo -e "  ${RED}✗${NC} Python 3 not found"
    echo -e "  ${YELLOW}→ Install Python 3.10+: https://www.python.org/downloads/${NC}"
    exit 1
fi

# ----------------------------------------------------------
# 2. Check FFmpeg
# ----------------------------------------------------------
echo -e "${BLUE}[2/6]${NC} Checking FFmpeg..."

if command -v ffmpeg &> /dev/null; then
    FF_VERSION=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    echo -e "  ${GREEN}✓${NC} FFmpeg $FF_VERSION detected"
else
    echo -e "  ${YELLOW}⚠${NC} FFmpeg not found (required for video merging)"
    echo -e "  ${YELLOW}→ Install via Homebrew: brew install ffmpeg${NC}"
    echo -e "  ${YELLOW}→ Or download from: https://ffmpeg.org/download.html${NC}"
    echo ""
    read -p "  Continue without FFmpeg? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi

# ----------------------------------------------------------
# 3. Create virtual environment
# ----------------------------------------------------------
echo -e "${BLUE}[3/6]${NC} Creating virtual environment..."

if [ -d "venv" ]; then
    echo -e "  ${YELLOW}⚠${NC} Virtual environment already exists, skipping"
else
    python3 -m venv venv
    echo -e "  ${GREEN}✓${NC} Virtual environment created at ./venv"
fi

# Activate venv
source venv/bin/activate
echo -e "  ${GREEN}✓${NC} Virtual environment activated"

# ----------------------------------------------------------
# 4. Install dependencies
# ----------------------------------------------------------
echo -e "${BLUE}[4/6]${NC} Installing dependencies..."

pip install --upgrade pip > /dev/null 2>&1
echo -e "  ${GREEN}✓${NC} pip upgraded"

pip install -r requirements.txt 2>&1 | while IFS= read -r line; do
    if [[ "$line" == *"Successfully installed"* ]]; then
        echo -e "  ${GREEN}✓${NC} $line"
    fi
done
echo -e "  ${GREEN}✓${NC} All dependencies installed"

# ----------------------------------------------------------
# 5. Create project directory structure
# ----------------------------------------------------------
echo -e "${BLUE}[5/6]${NC} Creating project structure..."

# Source directories
mkdir -p src/core
mkdir -p src/models
mkdir -p src/ui
mkdir -p src/utils

# Other directories
mkdir -p tests
mkdir -p assets
mkdir -p downloads

# Create __init__.py files
touch src/__init__.py
touch src/core/__init__.py
touch src/models/__init__.py
touch src/ui/__init__.py
touch src/utils/__init__.py

echo -e "  ${GREEN}✓${NC} Directory structure created"

# ----------------------------------------------------------
# 6. Verify installation
# ----------------------------------------------------------
echo -e "${BLUE}[6/6]${NC} Verifying installation..."

python3 -c "import yt_dlp; print(f'  yt-dlp {yt_dlp.version.__version__}')" 2>/dev/null && echo -e "  ${GREEN}✓${NC} yt-dlp OK" || echo -e "  ${RED}✗${NC} yt-dlp import failed"
python3 -c "import gallery_dl; print(f'  gallery-dl {gallery_dl.version.__version__}')" 2>/dev/null && echo -e "  ${GREEN}✓${NC} gallery-dl OK" || echo -e "  ${RED}✗${NC} gallery-dl import failed"

echo ""
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║                  Setup Complete! ✓                   ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  To activate the environment:                        ║"
echo "║    source venv/bin/activate                          ║"
echo "║                                                      ║"
echo "║  To start developing:                                ║"
echo "║    python -m src.main                                ║"
echo "║                                                      ║"
echo "║  Downloads will be saved to: ./downloads/            ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"
