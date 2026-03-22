"""Clipboard Utilities — Monitor and read clipboard for URLs.

Provides clipboard reading and optional monitoring for auto-detecting
URLs that the user copies while the app is running.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}"
    r"(?:/[^\s]*)?$"
)


def read_clipboard() -> str:
    """Read current clipboard contents.

    Returns:
        Clipboard text content, or empty string on failure.
    """
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception as e:
        logger.debug(f"Clipboard read failed: {e}")
        return ""


def is_url(text: str) -> bool:
    """Check if text looks like a URL.

    Args:
        text: Text to check.

    Returns:
        True if text appears to be a URL.
    """
    text = text.strip()
    return bool(_URL_PATTERN.match(text))


class ClipboardMonitor:
    """Monitors clipboard for new URLs.

    Runs a background thread that periodically checks the clipboard.
    When a new URL is detected, calls the registered callback.
    """

    def __init__(
        self,
        callback: Callable[[str], None],
        interval: float = 1.0,
    ) -> None:
        """Initialize the clipboard monitor.

        Args:
            callback: Function to call when a new URL is detected.
            interval: Seconds between clipboard checks.
        """
        self._callback = callback
        self._interval = interval
        self._last_content = ""
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start monitoring the clipboard."""
        if self._running:
            return

        self._running = True
        self._last_content = read_clipboard()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="clipboard-monitor",
        )
        self._thread.start()
        logger.info("Clipboard monitoring started")

    def stop(self) -> None:
        """Stop monitoring the clipboard."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Clipboard monitoring stopped")

    @property
    def is_running(self) -> bool:
        """Check if the monitor is currently running."""
        return self._running

    def _monitor_loop(self) -> None:
        """Background loop that checks clipboard periodically."""
        while self._running:
            try:
                content = read_clipboard()
                if content and content != self._last_content:
                    self._last_content = content
                    if is_url(content):
                        logger.info(f"New URL detected in clipboard: {content[:80]}...")
                        self._callback(content)
            except Exception as e:
                logger.debug(f"Clipboard monitor error: {e}")

            time.sleep(self._interval)
