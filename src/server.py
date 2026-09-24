"""HTTP server for Snag — allows remote download triggers.

Every ``/download`` request must carry ``Authorization: Bearer <token>``. The
token comes from the ``SNAG_SERVER_TOKEN`` environment variable, or is generated
once and stored (owner-only) at ``~/Library/Application Support/Snag/server_token``.
This stops other local processes, web pages (via DNS rebinding), and — if the
server is bound beyond localhost — other machines from triggering downloads.
"""

import hmac
import logging
import os
import secrets
import threading
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify

from src.core.url_router import URLRouter
from src.core.engine import DownloadOptions

logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN_ENV_VAR = "SNAG_SERVER_TOKEN"
_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def token_file() -> Path:
    """Return the path where the generated server token is stored."""
    return Path.home() / "Library" / "Application Support" / "Snag" / "server_token"


def load_or_create_token() -> str:
    """Return the server auth token, generating and persisting one if needed.

    Returns:
        The token from ``SNAG_SERVER_TOKEN`` if set, else the stored token,
        else a newly generated token written to :func:`token_file` with 0600
        permissions.
    """
    env_token = os.environ.get(TOKEN_ENV_VAR, "").strip()
    if env_token:
        return env_token

    path = token_file()
    if path.exists():
        stored = path.read_text().strip()
        if stored:
            return stored

    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token + "\n")
    path.chmod(0o600)
    logger.info("Generated new server token at %s", path)
    return token


class SnagServer:
    """HTTP server that wraps Snag's download engine."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.router = URLRouter()
        self.token = load_or_create_token()
        self._thread: Optional[threading.Thread] = None

    def is_authorized(self, auth_header: Optional[str]) -> bool:
        """Check an ``Authorization`` header against the server token."""
        if not auth_header or not auth_header.startswith("Bearer "):
            return False
        supplied = auth_header[len("Bearer "):].strip()
        return hmac.compare_digest(supplied.encode(), self.token.encode())

    def download(self, url: str) -> dict:
        """Download a URL using Snag's engine."""
        try:
            logger.info(f"HTTP request to download: {url}")

            # Use default download options
            options = DownloadOptions()

            # Route the URL to appropriate backend
            result = self.router.download(url, options)

            if result.success:
                title = result.media_info.title if result.media_info else "Unknown"
                filepath = result.filepath
                return {
                    "success": True,
                    "url": url,
                    "title": title,
                    # File name only — don't reveal the local directory layout
                    "filename": Path(filepath).name if filepath else None,
                    "message": "Download completed successfully"
                }
            else:
                return {
                    "success": False,
                    "url": url,
                    "error": result.error or "Unknown error",
                    "message": "Download failed"
                }
        except Exception as e:
            logger.error(f"Download failed: {e}", exc_info=True)
            return {
                "success": False,
                "url": url,
                "error": "Internal error — see server log",
                "message": "Download failed"
            }

    def start(self, daemon: bool = True):
        """Start the HTTP server in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Server already running")
            return

        # Set up routes
        @app.route('/download', methods=['POST'])
        def download_endpoint():
            if not self.is_authorized(request.headers.get("Authorization")):
                return jsonify({"error": "Unauthorized"}), 401

            data = request.get_json(silent=True)
            if not isinstance(data, dict) or not isinstance(data.get('url'), str):
                return jsonify({"error": "Missing 'url' in JSON body"}), 400

            url = data['url'].strip()
            if not url:
                return jsonify({"error": "URL cannot be empty"}), 400
            if not URLRouter.is_valid_url(url):
                return jsonify({"error": "URL must be an http(s) URL"}), 400

            result = self.download(url)
            status_code = 200 if result['success'] else 500
            return jsonify(result), status_code

        @app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "ok", "service": "snag"})

        def run():
            logger.info(f"Starting Snag HTTP server on {self.host}:{self.port}")
            if self.host not in _LOOPBACK_HOSTS:
                logger.warning(
                    "Server is reachable from other machines on %s — traffic is "
                    "unencrypted HTTP; only do this on a trusted network", self.host
                )
            if os.environ.get(TOKEN_ENV_VAR):
                logger.info("Auth token: from $%s", TOKEN_ENV_VAR)
            else:
                logger.info("Auth token: %s", token_file())
            app.run(host=self.host, port=self.port, debug=False, use_reloader=False)

        self._thread = threading.Thread(target=run, daemon=daemon)
        self._thread.start()
        logger.info(f"Server thread started (daemon={daemon})")

    def stop(self):
        """Stop the HTTP server."""
        # Flask doesn't have a clean stop, but we can kill the thread
        if self._thread and self._thread.is_alive():
            # We'd need Werkzeug's shutdown for clean stop
            # For now, just mark for cleanup
            logger.warning("Server stop requested (requires process termination)")


def main():
    """Standalone server entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Snag HTTP Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = SnagServer(host=args.host, port=args.port)
    server.start(daemon=False)  # Run in foreground


if __name__ == '__main__':
    main()
