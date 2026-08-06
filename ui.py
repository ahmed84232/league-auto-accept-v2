import html
import os
import subprocess
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizeGrip, QVBoxLayout, QWidget,
)

from styles import LOG_COLORS, PALETTE
from updater import (
    UPDATER_SCRIPT, UpdateChecker, UpdateDownloader,
    extract_update, pythonw_executable,
)
from version import __version__
from worker import AutoAcceptWorker

OWNER = "ahmed84232"
REPO = "league-auto-accept-v2"

PHASE_META = {
    "None": ("idle", "Idle"),
    "Lobby": ("lobby", "Lobby"),
    "Matchmaking": ("matchmaking", "Searching..."),
    "ReadyCheck": ("readycheck", "Match Found!"),
    "ChampSelect": ("champselect", "Champion Select"),
    "InProgress": ("ingame", "In Game"),
    "InGame": ("ingame", "In Game"),
    "Searching...": ("searching", "Searching for client..."),
    "Stopped": ("stopped", "Stopped"),
}

LOG_ICONS = {
    "info": "●",
    "success": "✓",
    "warning": "▲",
    "error": "✕",
}


class TitleBar(QWidget):

    def __init__(self, parent, title):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 10, 0)
        layout.setSpacing(8)

        dot = QLabel("●")
        dot.setObjectName("appDot")
        layout.addWidget(dot)

        title_label = QLabel(title)
        title_label.setObjectName("appTitle")
        layout.addWidget(title_label)

        layout.addStretch()

        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("windowBtn")
        self.min_btn.setFixedSize(36, 28)
        self.min_btn.clicked.connect(parent.showMinimized)
        layout.addWidget(self.min_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("windowBtnClose")
        self.close_btn.setFixedSize(36, 28)
        self.close_btn.clicked.connect(parent.close)
        layout.addWidget(self.close_btn)

        self._drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint()
                - self.window().frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowTitle("League Auto-Accept")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setMinimumSize(460, 640)
        self.resize(480, 720)

        self.worker = None
        self._checker = None
        self._downloader = None
        self._update_staging = None
        self._update_zip = None
        self.matches_accepted = 0
        self._is_running = False

        self._setup_ui()

        QTimer.singleShot(3000, lambda: self._check_for_updates())

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self, "League Auto-Accept")
        root.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)

        content_layout.addWidget(self._create_status_card())
        content_layout.addWidget(self._create_log_card(), 1)
        content_layout.addWidget(self._create_control_panel())

        root.addWidget(content, 1)

    def _make_card(self):
        card = QFrame()
        card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 140))
        card.setGraphicsEffect(shadow)
        return card

    def _create_status_card(self):
        card = self._make_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()

        self.conn_dot = QLabel("●")
        self.conn_dot.setObjectName("connectionDot")
        self.conn_dot.setProperty("state", "disconnected")
        top.addWidget(self.conn_dot)

        self.conn_label = QLabel("Disconnected")
        self.conn_label.setObjectName("connectionLabel")
        top.addWidget(self.conn_label)
        top.addStretch()

        matches_box = QVBoxLayout()
        matches_box.setSpacing(0)
        self.matches_value = QLabel("0")
        self.matches_value.setObjectName("matchesValue")
        self.matches_value.setAlignment(Qt.AlignRight)
        matches_label = QLabel("MATCHES ACCEPTED")
        matches_label.setObjectName("matchesLabel")
        matches_label.setAlignment(Qt.AlignRight)
        matches_box.addWidget(self.matches_value)
        matches_box.addWidget(matches_label)
        top.addLayout(matches_box)

        layout.addLayout(top)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        phase_label = QLabel("CURRENT PHASE")
        phase_label.setObjectName("sectionLabel")
        layout.addWidget(phase_label)

        self.phase_badge = QLabel("  Stopped  ")
        self.phase_badge.setObjectName("phaseBadge")
        self.phase_badge.setProperty("phase", "stopped")
        self.phase_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.phase_badge, alignment=Qt.AlignCenter)

        return card

    def _create_log_card(self):
        card = self._make_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header_label = QLabel("ACTIVITY LOG")
        header_label.setObjectName("logHeader")
        header.addWidget(header_label)
        header.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self._clear_log)
        header.addWidget(self.clear_btn)
        layout.addLayout(header)

        self.log_scroll = QScrollArea()
        self.log_scroll.setWidgetResizable(True)
        self.log_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.log_scroll.setFrameShape(QFrame.NoFrame)

        self.log_container = QWidget()
        self.log_container.setObjectName("root")
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setContentsMargins(2, 2, 6, 2)
        self.log_layout.setSpacing(2)
        self.log_layout.addStretch()

        self.log_scroll.setWidget(self.log_container)
        layout.addWidget(self.log_scroll, 1)

        return card

    def _create_control_panel(self):
        panel = QWidget()
        panel.setObjectName("root")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.toggle_btn = QPushButton("▶  START AUTO-ACCEPT")
        self.toggle_btn.setObjectName("primaryButton")
        self.toggle_btn.setProperty("state", "start")
        self.toggle_btn.setMinimumHeight(56)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_service)
        layout.addWidget(self.toggle_btn)

        self.progress = QProgressBar()
        self.progress.setObjectName("updateProgress")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)

        hint = QLabel("Waits for match and accepts instantly")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        footer = QHBoxLayout()
        footer.setContentsMargins(4, 0, 4, 0)
        version_label = QLabel(f"v{__version__}")
        version_label.setObjectName("versionLabel")
        footer.addWidget(version_label)

        footer.addStretch()

        self.update_btn = QPushButton("Check for updates")
        self.update_btn.setObjectName("linkButton")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.clicked.connect(lambda: self._check_for_updates(manual=True))
        footer.addWidget(self.update_btn)

        layout.addLayout(footer)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()
        grip_row.addWidget(QSizeGrip(panel))
        layout.addLayout(grip_row)

        return panel

    def _refresh_property(self, widget, name, value):
        widget.setProperty(name, value)
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)

    def _add_log_entry(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = LOG_COLORS.get(level, LOG_COLORS["info"])
        icon = LOG_ICONS.get(level, LOG_ICONS["info"])
        safe_message = html.escape(message)

        entry = QLabel(
            f'<span style="color:{PALETTE["MUTED"]}">{timestamp}</span>'
            f'  <span style="color:{color}">{icon}</span>'
            f'  <span style="color:{PALETTE["TEXT"]}">{safe_message}</span>'
        )
        entry.setObjectName("logEntry")
        entry.setTextFormat(Qt.RichText)
        entry.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.log_layout.insertWidget(self.log_layout.count() - 1, entry)

        QTimer.singleShot(0, lambda: self.log_scroll.verticalScrollBar().setValue(
            self.log_scroll.verticalScrollBar().maximum()
        ))

    def _clear_log(self):
        while self.log_layout.count() > 1:
            item = self.log_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _update_phase(self, phase):
        token, display = PHASE_META.get(phase, ("idle", phase))
        self._refresh_property(self.phase_badge, "phase", token)
        self.phase_badge.setText(f"  {display}  ")

    def _update_connected(self, connected):
        state = "connected" if connected else "disconnected"
        self._refresh_property(self.conn_dot, "state", state)
        self.conn_label.setText(
            "Connected to League Client" if connected else "Disconnected"
        )

    def _on_match_accepted(self):
        self.matches_accepted += 1
        self.matches_value.setText(str(self.matches_accepted))

    def _check_for_updates(self, manual=False):
        if self._checker is not None and self._checker.isRunning():
            return
        if manual:
            self._add_log_entry("Checking for updates...", "info")
        self._checker = UpdateChecker(OWNER, REPO, __version__, parent=self)
        self._checker.result_signal.connect(
            lambda ok, has_update, tag, body, url, download_url:
                self._on_update_result(ok, has_update, tag, body, url, download_url, manual)
        )
        self._checker.start()

    def _on_update_result(self, ok, has_update, tag, body, url, download_url, manual):
        if not ok:
            self._add_log_entry("Update check failed (network or GitHub issue).", "warning")
            if manual:
                QMessageBox.warning(
                    self, "Update check failed",
                    "Could not reach GitHub. Check your internet connection.",
                )
            return

        if has_update:
            self._add_log_entry(f"Update available: {tag}", "success")
            self._show_update_dialog(tag, body, url, download_url)
        elif manual:
            self._add_log_entry("You're up to date.", "success")
            QMessageBox.information(
                self, "Up to date",
                f"You're running the latest version (v{__version__}).",
            )

    def _show_update_dialog(self, tag, body, url, download_url):
        msg = QMessageBox(self)
        msg.setWindowTitle("Update available")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"A new version is available: {tag}")
        msg.setInformativeText(body.strip() or "No release notes.")

        update_btn = None
        if download_url:
            update_btn = msg.addButton("Download & Update", QMessageBox.ActionRole)
        open_btn = msg.addButton("Open GitHub", QMessageBox.ActionRole)
        msg.addButton("Later", QMessageBox.RejectRole)
        msg.exec()

        clicked = msg.clickedButton()
        if update_btn and clicked is update_btn:
            self._start_update(download_url)
        elif clicked is open_btn:
            QDesktopServices.openUrl(QUrl(url))

    def _start_update(self, download_url):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        staging = os.path.join(app_dir, ".update")
        os.makedirs(staging, exist_ok=True)

        self._update_staging = staging
        self._update_zip = os.path.join(staging, "update.zip")

        self._add_log_entry("Downloading update...", "info")
        self.progress.setValue(0)
        self.progress.show()
        self.update_btn.setEnabled(False)

        self._downloader = UpdateDownloader(download_url, self._update_zip, parent=self)
        self._downloader.progress_signal.connect(self.progress.setValue)
        self._downloader.done_signal.connect(self._on_download_done)
        self._downloader.start()

    def _on_download_done(self, ok, message):
        if not ok:
            self._add_log_entry(f"Update download failed: {message}", "error")
            self.progress.hide()
            self.update_btn.setEnabled(True)
            return
        self._add_log_entry("Download complete, applying update...", "info")
        self._apply_update()

    def _apply_update(self):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        extract_dir = os.path.join(self._update_staging, "extracted")

        try:
            source_dir = extract_update(self._update_zip, extract_dir)
        except Exception as exc:
            self._add_log_entry(f"Failed to unpack update: {exc}", "error")
            self.progress.hide()
            self.update_btn.setEnabled(True)
            return

        updater_path = os.path.join(self._update_staging, "updater.pyw")
        with open(updater_path, "w", encoding="utf-8") as f:
            f.write(UPDATER_SCRIPT)

        interpreter = pythonw_executable()
        launcher = os.path.join(app_dir, "main.pyw")
        if not os.path.exists(launcher):
            launcher = os.path.join(app_dir, "main.py")

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [interpreter, updater_path, app_dir, source_dir,
             str(os.getpid()), interpreter, launcher],
            cwd=app_dir,
            close_fds=True,
            creationflags=flags,
        )
        self._add_log_entry("Restarting to finish update...", "success")
        self.close()

    def _toggle_service(self):
        if self._is_running:
            self._stop_service()
        else:
            self._start_service()

    def _start_service(self):
        if self._is_running or (self.worker and self.worker.isRunning()):
            return

        self._is_running = True
        self._refresh_property(self.toggle_btn, "state", "stop")
        self.toggle_btn.setText("■  STOP AUTO-ACCEPT")

        self._add_log_entry("Starting Auto-Accept...", "info")

        self.worker = AutoAcceptWorker()
        self.worker.log_signal.connect(self._add_log_entry)
        self.worker.phase_signal.connect(self._update_phase)
        self.worker.connected_signal.connect(self._update_connected)
        self.worker.match_accepted_signal.connect(self._on_match_accepted)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self):
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _stop_service(self):
        self._is_running = False
        self._refresh_property(self.toggle_btn, "state", "start")
        self.toggle_btn.setText("▶  START AUTO-ACCEPT")

        if self.worker:
            self.worker.stop()
            self.worker.wait(3000)

        self._add_log_entry("Stopped Auto-Accept", "info")
        self._update_phase("Stopped")
        self._update_connected(False)

    def closeEvent(self, event):
        self._stop_service()
        if self._checker:
            self._checker.wait(6000)
        if self._downloader:
            self._downloader.wait(60000)
        event.accept()
