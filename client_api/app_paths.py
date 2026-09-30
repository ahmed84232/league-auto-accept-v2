"""Single place that knows where the app lives on disk.

Saved files and update staging always resolve to the folder with
main.pyw and version.py, no matter which module asks. This keeps
the self-updater working after the folder split.
"""

import os

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SESSION_FILE = os.path.join(APP_DIR, "session.json")
HISTORY_FILE = os.path.join(APP_DIR, "history.json")
