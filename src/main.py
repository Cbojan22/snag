"""Snag — Entry Point."""

import fcntl
import os
import sys
import logging
import tempfile
import argparse
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
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Snag — download videos and images at highest quality")
    parser.add_argument(
        "--server",
        action="store_true",
        help="Start HTTP server instead of GUI (runs in background)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP server (default: 8080)"
    )
    return parser.parse_args()


def main() -> None:
    """Application entry point."""
    args = parse_args()
    setup_logging()
    logger = logging.getLogger(__name__)
    
    ensure_path()
    lock = acquire_lock()
    
    try:
        if args.server:
            # Start HTTP server mode
            from src.server import SnagServer
            logger.info(f"Starting Snag HTTP server on {args.host}:{args.port}")
            server = SnagServer(host=args.host, port=args.port)
            server.start(daemon=False)  # Run in foreground
        else:
            # Start GUI mode
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
