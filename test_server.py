#!/usr/bin/env python3
"""Test the Snag HTTP server."""

import json
import requests
import time
from pathlib import Path

from src.server import load_or_create_token

PROJECT_ROOT = Path(__file__).resolve().parent


def test_server():
    # Start the server (in background)
    import subprocess
    import sys
    import threading

    def run_server():
        subprocess.run([
            sys.executable, "-m", "src.main", "--server", "--host", "127.0.0.1", "--port", "8080"
        ], cwd=PROJECT_ROOT)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(3)

    # Test health endpoint
    try:
        resp = requests.get("http://127.0.0.1:8080/health")
        print(f"Health check: {resp.status_code} - {resp.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # Test download endpoint
    test_url = "https://youtu.be/Ru4owY1Mu0Q?si=kAwVm7DBrJi-lvZJ"
    payload = {"url": test_url}
    headers = {"Authorization": f"Bearer {load_or_create_token()}"}

    try:
        resp = requests.post("http://127.0.0.1:8080/download", json=payload, headers=headers)
        print(f"Download response: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))
    except Exception as e:
        print(f"Download test failed: {e}")

if __name__ == "__main__":
    test_server()
