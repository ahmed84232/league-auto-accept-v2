import html
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QScrollArea, QSizeGrip, QVBoxLayout, QWidget,
)

from styles import LOG_COLORS, PALETTE
from worker import AutoAcceptWorker

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
        self.matches_accepted = 0
        self._is_running = False

        self._setup_ui()

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

        hint = QLabel("Waits for match and accepts instantly")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

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
        event.accept()
