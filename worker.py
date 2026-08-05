import base64
import os
import time
import urllib3

import psutil
import requests
from PySide6.QtCore import QThread, Signal

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AutoAcceptWorker(QThread):

    log_signal = Signal(str, str)
    phase_signal = Signal(str)
    connected_signal = Signal(bool)
    match_accepted_signal = Signal()

    CLIENT_PROCESS = "LeagueClientUx.exe"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._lockfile = None
        self._last_log = None

    def stop(self):
        self._running = False

    def find_lockfile(self):
        cached = self._lockfile
        if cached and os.path.exists(cached):
            return cached

        for proc in psutil.process_iter(["name", "exe"]):
            try:
                if proc.info["name"] == self.CLIENT_PROCESS and proc.info["exe"]:
                    lockfile = os.path.join(os.path.dirname(proc.info["exe"]), "lockfile")
                    if os.path.exists(lockfile):
                        self._lockfile = lockfile
                        return lockfile
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        self._lockfile = None
        return None

    @staticmethod
    def read_credentials(lockfile):
        with open(lockfile, "r", encoding="utf-8") as f:
            parts = f.read().strip().split(":")
        return parts[2], base64.b64encode(f"riot:{parts[3]}".encode()).decode()

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while self._running and time.monotonic() < end:
            time.sleep(0.2)

    def _log(self, message, level="info"):
        if (message, level) != self._last_log:
            self._last_log = (message, level)
            self.log_signal.emit(message, level)

    def run(self):
        if not self._running:
            return

        session = requests.Session()
        session.verify = False
        session.headers["Accept"] = "application/json"

        try:
            while self._running:
                lockfile = self.find_lockfile()
                if not lockfile:
                    self._log("LeagueClientUx.exe process not found.", "warning")
                    self.connected_signal.emit(False)
                    self.phase_signal.emit("Searching...")
                    self._sleep(3)
                    continue

                try:
                    port, auth = self.read_credentials(lockfile)
                except (IndexError, OSError) as exc:
                    self._log(f"Failed to read lockfile: {exc}", "error")
                    self.connected_signal.emit(False)
                    self._sleep(3)
                    continue

                session.headers["Authorization"] = f"Basic {auth}"
                self._log(f"Connected to client (port {port})", "success")
                self.connected_signal.emit(True)

                self._poll(session, port)

                if not self._running:
                    break

                self._log("Lost connection, reconnecting...", "warning")
                self.connected_signal.emit(False)
                self._sleep(3)
        finally:
            session.close()
            self.connected_signal.emit(False)
            self.phase_signal.emit("Stopped")

    def _poll(self, session, port):
        base = f"https://127.0.0.1:{port}"
        phase_url = f"{base}/lol-gameflow/v1/gameflow-phase"
        ready_check = f"{base}/lol-matchmaking/v1/ready-check"
        accept = f"{base}/lol-matchmaking/v1/ready-check/accept"

        while self._running:
            try:
                phase_resp = session.get(phase_url, timeout=5)
                phase = None if phase_resp.status_code == 404 else phase_resp.json()
                self.phase_signal.emit(phase or "None")

                if phase in ("InProgress", "InGame"):
                    self._log("Game in progress...", "info")
                    self._sleep(10)
                    continue

                if phase == "ChampSelect":
                    self._sleep(5)
                    continue

                rc = session.get(ready_check, timeout=5)
                if rc.status_code == 404:
                    self._log("Waiting for you to press Find Match...", "info")
                    self._sleep(3)
                    continue

                state = rc.json().get("state")
                if state == "Invalid":
                    self._log("No match found yet", "info")
                    self._sleep(2)
                elif state == "InProgress":
                    self._log("Match Found", "success")
                    session.post(accept, timeout=5)
                    self._log("Match accepted!", "success")
                    self.match_accepted_signal.emit()
                    self._sleep(5)
                elif state == "Searching":
                    self._sleep(2)
                else:
                    self._log("Waiting for you to press Find Match...", "info")
                    self._sleep(5)
            except (requests.RequestException, ValueError) as exc:
                self._log(f"Connection error: {exc}", "error")
                return
