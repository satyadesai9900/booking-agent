"""
Convenience launcher for the LangGraph Agent & React UI.
Runs the Python backend server and automatically opens the React UI in your browser.
"""

import sys
import time
import webbrowser
import threading

# Ensure proper encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from server import app

PORT = 5000
URL = f"http://127.0.0.1:{PORT}"


def open_browser():
    """Waits for server to initialize then opens the web interface."""
    time.sleep(1.2)
    print(f"\n[Browser] Opening React UI at {URL} ...\n")
    webbrowser.open(URL)


def main():
    print("=" * 65)
    print("  LangGraph Gemini AI Agent with React UI")
    print(f"  Server URL:    {URL}")
    print("  API Key:       Securely managed via backend env/.env")
    print("  Checkpointer:  MemorySaver (stateful per thread)")
    print("=" * 65)

    # Launch browser in separate background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run the Flask web & API server
    app.run(host="127.0.0.1", port=PORT, debug=False)


if __name__ == "__main__":
    main()
