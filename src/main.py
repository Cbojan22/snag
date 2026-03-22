"""Snag — Entry Point."""

import sys
import logging
from src.app import SnagApp


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    """Launch the Snag application."""
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


if __name__ == "__main__":
    main()
