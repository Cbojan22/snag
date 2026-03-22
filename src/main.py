"""Snag — Entry Point."""

import fcntl
import os
import sys
import logging
import tempfile
from src.app import SnagApp


LOCK_FILE = os.path.join(tempfile.gettempdir(), "snag.lock")

# Common paths where ffmpeg/yt-dlp might be installed on macOS
_EXTRA_PATHS = [
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/opt/local/bin",
    os.path.expanduser("~/.local/bin"),
]


def ensure_path() -> None:
    """Ensure common tool directories are on PATH.

    PyInstaller bundles don't always inherit the user's full PATH,
    so ffmpeg and other CLI tools may not be found.
    """
    current = os.environ.get("PATH", "")
    missing = [p for p in _EXTRA_PATHS if p not in current and os.path.isdir(p)]
    if missing:
        os.environ["PATH"] = current + ":" + ":".join(missing)


def acquire_lock():
    """Ensure only one instance of Snag is running.

    Uses a file lock — if another instance holds it, we exit.
    """
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        # Another instance is already running
        print("Snag is already running.")
        sys.exit(0)
    # Keep the fd open for the lifetime of the process
    return lock_fd


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    """Launch the Snag application."""
    lock = acquire_lock()
    ensure_path()
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Snag...")

    try:
        app = SnagApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        lock.close()


if __name__ == "__main__":
    # Required for PyInstaller on macOS — prevents spawned
    # child processes from opening duplicate windows
    import multiprocessing
    multiprocessing.freeze_support()
    main()
