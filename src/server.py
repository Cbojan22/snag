"""HTTP server for Snag — allows remote download triggers."""

import json
import logging
import threading
from typing import Optional

from flask import Flask, request, jsonify

from src.core.url_router import URLRouter
from src.core.engine import DownloadOptions

logger = logging.getLogger(__name__)

app = Flask(__name__)


class SnagServer:
    """HTTP server that wraps Snag's download engine."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.router = URLRouter()
        self._thread: Optional[threading.Thread] = None

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
                    "filepath": str(filepath) if filepath else None,
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
                "error": str(e),
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
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({"error": "Missing 'url' in JSON body"}), 400
            
            url = data['url'].strip()
            if not url:
                return jsonify({"error": "URL cannot be empty"}), 400
            
            result = self.download(url)
            status_code = 200 if result['success'] else 500
            return jsonify(result), status_code
        
        @app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "ok", "service": "snag"})
        
        def run():
            logger.info(f"Starting Snag HTTP server on {self.host}:{self.port}")
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
