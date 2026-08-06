import re

import requests
from PySide6.QtCore import QThread, Signal


def _version_tuple(version):
    return tuple(int(x) for x in re.findall(r"\d+", version) or [0])


def is_newer(latest, current):
    return _version_tuple(latest) > _version_tuple(current)


class UpdateChecker(QThread):

    result_signal = Signal(bool, bool, str, str, str)  # ok, has_update, tag, body, url

    def __init__(self, owner, repo, current_version, parent=None):
        super().__init__(parent)
        self._owner = owner
        self._repo = repo
        self._current = current_version

    def run(self):
        try:
            url = f"https://api.github.com/repos/{self._owner}/{self._repo}/releases/latest"
            resp = requests.get(
                url, timeout=10, headers={"User-Agent": "league-auto-accept-v2"}
            )
            if resp.status_code != 200:
                self.result_signal.emit(False, False, "", "", "")
                return

            data = resp.json()
            tag = data.get("tag_name", "")
            body = data.get("body", "")
            html_url = data.get("html_url", "")
            has_update = is_newer(tag, self._current)
            self.result_signal.emit(True, has_update, tag, body, html_url)
        except requests.RequestException:
            self.result_signal.emit(False, False, "", "", "")
