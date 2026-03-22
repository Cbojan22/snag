"""Snag — Application Bootstrap."""

import logging

from src.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class SnagApp:
    """Main application controller."""

    def __init__(self) -> None:
        logger.info("Initializing Snag...")
        self._window = MainWindow()

    def run(self) -> None:
        """Start the application main loop."""
        self._window.run()
