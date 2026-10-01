"""Service coordinator: owns worker + updater threads (no QML).

QML renders and confirms dialogs; this class runs everything
else and reports through signals. Log strings are byte-identical to
the pre-extraction app so behaviour is unchanged.
"""

import os
import subprocess

from PySide6.QtCore import QObject, Signal

from client_api.app_paths import APP_DIR
from client_api.updater import (
    UPDATER_SCRIPT, UpdateChecker, UpdateDownloader,
    extract_update, pythonw_executable,
)
from client_api.worker import AutoAcceptWorker


class ServiceCoordinator(QObject):
    log_requested = Signal(str, str)
    phase_changed = Signal(str)
    connected_changed = Signal(bool)
    running_changed = Signal(bool)
    match_accepted = Signal()
    game_started = Signal()
    game_result = Signal(dict)
    game_result_correction = Signal(dict)
    update_progress = Signal(int)
    update_check_failed = Signal(bool)  # manual
    update_available = Signal(str, str, str, str)  # tag, body, url, download_url
    update_up_to_date = Signal()
    update_download_failed = Signal(str)
    restart_requested = Signal()

    def __init__(self, owner, repo, version, parent=None):
        super().__init__(parent)
        self._owner = owner
        self._repo = repo
        self._version = version
        self._is_running = False
        self.worker = None
        self._checker = None
        self._downloader = None
        self._update_staging = None
        self._update_zip = None
        self._update_tag = ""

    # -- auto-accept service -------------------------------------------

    def is_running(self):
        return self._is_running

    def toggle_service(self):
        if self._is_running:
            self.stop_service()
        else:
            self.start_service()
        return self._is_running

    def start_service(self):
        if self._is_running or (self.worker and self.worker.isRunning()):
            return
        self._is_running = True
        self.running_changed.emit(True)
        self.log_requested.emit("Starting Auto-Accept...", "info")

        self.worker = AutoAcceptWorker()
        self.worker.log_signal.connect(self.log_requested.emit)
        self.worker.phase_signal.connect(self.phase_changed.emit)
        self.worker.connected_signal.connect(self.connected_changed.emit)
        self.worker.match_accepted_signal.connect(self.match_accepted.emit)
        self.worker.game_started_signal.connect(self.game_started.emit)
        self.worker.game_result_signal.connect(self.game_result.emit)
        self.worker.game_result_correction_signal.connect(
            self.game_result_correction.emit)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self):
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def stop_service(self):
        self._is_running = False
        self.running_changed.emit(False)
        if self.worker:
            self.worker.stop()
            self.worker.wait(3000)
        self.log_requested.emit("Stopped Auto-Accept", "info")
        self.phase_changed.emit("Stopped")
        self.connected_changed.emit(False)

    # -- updates ---------------------------------------------------------

    def check_for_updates(self, manual=False):
        if self._checker is not None and self._checker.isRunning():
            return
        if manual:
            self.log_requested.emit("Checking for updates...", "info")
        self._checker = UpdateChecker(
            self._owner, self._repo, self._version, parent=self)
        self._checker.result_signal.connect(
            lambda ok, has_update, tag, body, url, download_url:
                self._on_update_result(
                    ok, has_update, tag, body, url, download_url, manual)
        )
        self._checker.start()

    def _on_update_result(self, ok, has_update, tag, body, url, download_url,
                          manual):
        if not ok:
            self.log_requested.emit(
                "Update check failed (network or GitHub issue).", "warning")
            self.update_check_failed.emit(manual)
            return
        if has_update:
            self.log_requested.emit(f"Update available: {tag}", "success")
            self.update_available.emit(tag, body, url, download_url)
        elif manual:
            self.log_requested.emit("You're up to date.", "success")
            self.update_up_to_date.emit()

    def begin_update(self, download_url, tag=""):
        staging = os.path.join(APP_DIR, ".update")
        os.makedirs(staging, exist_ok=True)

        self._update_staging = staging
        self._update_zip = os.path.join(staging, "update.zip")
        self._update_tag = tag

        self.log_requested.emit("Downloading update...", "info")
        self._downloader = UpdateDownloader(
            download_url, self._update_zip, parent=self)
        self._downloader.progress_signal.connect(self.update_progress.emit)
        self._downloader.done_signal.connect(self._on_download_done)
        self._downloader.start()

    def _on_download_done(self, ok, message):
        if not ok:
            self.log_requested.emit(
                f"Update download failed: {message}", "error")
            self.update_download_failed.emit(message)
            return
        self.log_requested.emit("Download complete, applying update...", "info")
        self._apply_update()

    def _apply_update(self):
        extract_dir = os.path.join(self._update_staging, "extracted")
        try:
            source_dir = extract_update(self._update_zip, extract_dir)
        except Exception as exc:
            self.log_requested.emit(f"Failed to unpack update: {exc}", "error")
            self.update_download_failed.emit(str(exc))
            return

        updater_path = os.path.join(self._update_staging, "updater.pyw")
        with open(updater_path, "w", encoding="utf-8") as f:
            f.write(UPDATER_SCRIPT)

        interpreter = pythonw_executable()
        launcher = os.path.join(APP_DIR, "main.pyw")
        if not os.path.exists(launcher):
            launcher = os.path.join(APP_DIR, "main.py")

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [interpreter, updater_path, APP_DIR, source_dir,
             str(os.getpid()), interpreter, launcher, self._update_tag],
            cwd=APP_DIR,
            close_fds=True,
            creationflags=flags,
        )
        self.log_requested.emit("Restarting to finish update...", "success")
        self.restart_requested.emit()

    def shutdown(self):
        self.stop_service()
        if self._checker:
            self._checker.wait(6000)
        if self._downloader:
            self._downloader.wait(60000)
