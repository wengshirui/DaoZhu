"""AccoBot Web — single-file entry point for PyInstaller exe."""

import sys
import os

# Ensure the bundled data path is discoverable
if getattr(sys, "frozen", False):
    # Running as PyInstaller bundle
    os.environ.setdefault("ACCOBOT_BUNDLE", sys._MEIPASS)

from accobot.web.server import start_server

if __name__ == "__main__":
    port = 9120
    # Simple --port arg parsing
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])
    start_server(host="127.0.0.1", port=port)
