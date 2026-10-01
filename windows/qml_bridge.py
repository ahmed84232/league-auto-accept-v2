"""QML bridge: the single seam between Python backend and QML views.

Backend (coordinator, session manager, stores) is untouched — this
QObject mirrors its state as Qt properties and forwards QML intents
as slot calls. No widgets here; dialogs live in QML.
"""

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from client_api import history_store, session_store
from windows.tokens import phase_style

MAX_HISTORY = 200


class QmlBridge(QObject):
    connectedChanged = Signal()
    phaseChanged = Signal()
    statsChanged = Signal()
    matchesChanged = Signal()
    runningChanged = Signal()
    elapsedChanged = Signal()
    logMessage = Signal(str, str)  # message, level
    historyChanged = Signal()
    updateCheckFailed = Signal(bool)  # manual
    updateAvailable = Signal(str, str, str, str)  # tag, body, url, dl
    updateUpToDate = Signal()
    updateDownloadFailed = Signal(str)
    updateProgressed = Signal(int)
    updateDownloadStarted = Signal()
    restartRequested = Signal()
    glassChanged = Signal()

    def __init__(self, coordinator, session, session_file, history_file,
                 max_history=MAX_HISTORY, parent=None):
        super().__init__(parent)
        self._coordinator = coordinator
        self._vm = session
        self._session_file = session_file
        self._history_file = history_file
        self._max_history = max_history
        self._connected = False
        self._phase = "Stopped"
        self._running = False
        self._accepted = 0
        self._played = 0
        self._elapsed = 0
        self._glass = False
        self._window = None

        c = coordinator
        c.log_requested.connect(self.logMessage.emit)
        c.phase_changed.connect(self._on_phase)
        c.connected_changed.connect(self._on_connected)
        c.running_changed.connect(self._on_running)
        c.match_accepted.connect(self._on_accepted)
        c.game_started.connect(self._on_played)
        c.game_result.connect(self._on_result)
        c.game_result_correction.connect(self._on_correction)
        c.update_progress.connect(self.updateProgressed.emit)
        c.update_check_failed.connect(self.updateCheckFailed.emit)
        c.update_available.connect(self.updateAvailable.emit)
        c.update_up_to_date.connect(self.updateUpToDate.emit)
        c.update_download_failed.connect(self.updateDownloadFailed.emit)
        c.restart_requested.connect(self.restartRequested.emit)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # -- properties (QML binds to these) -------------------------------

    def _get_connected(self):
        return self._connected

    connected = Property(bool, _get_connected, notify=connectedChanged)

    def _get_phase_label(self):
        return phase_style(self._phase)[0]

    def _get_phase_color(self):
        return phase_style(self._phase)[1]

    phaseLabel = Property(str, _get_phase_label, notify=phaseChanged)
    phaseColor = Property(str, _get_phase_color, notify=phaseChanged)

    def _get_running(self):
        return self._running

    running = Property(bool, _get_running, notify=runningChanged)

    def _get_wins(self):
        return self._vm.session.get("wins", 0)

    def _get_losses(self):
        return self._vm.session.get("losses", 0)

    def _get_remakes(self):
        return self._vm.session.get("remakes", 0)

    def _get_net_lp(self):
        return self._vm.session.get("lp_delta", 0)

    wins = Property(int, _get_wins, notify=statsChanged)
    losses = Property(int, _get_losses, notify=statsChanged)
    remakes = Property(int, _get_remakes, notify=statsChanged)
    netLp = Property(int, _get_net_lp, notify=statsChanged)

    def _get_rank_title(self):
        s = self._vm.session
        if s.get("tier") and s.get("division"):
            return "%s %s" % (s["tier"], s["division"])
        return "Unranked"

    def _get_rank_lp(self):
        s = self._vm.session
        if s.get("tier") and s.get("division"):
            return ("%s LP" % s["lp"]) if s.get("lp") is not None else ""
        return ""

    rankTitle = Property(str, _get_rank_title, notify=statsChanged)
    rankLp = Property(str, _get_rank_lp, notify=statsChanged)

    def _get_accepted(self):
        return self._accepted

    def _get_played(self):
        return self._played

    accepted = Property(int, _get_accepted, notify=matchesChanged)
    played = Property(int, _get_played, notify=matchesChanged)

    def _get_elapsed(self):
        return self._elapsed

    elapsedSecs = Property(int, _get_elapsed, notify=elapsedChanged)

    def _get_glass(self):
        return self._glass

    glassActive = Property(bool, _get_glass, notify=glassChanged)

    def set_glass_active(self, active=True):
        self._glass = bool(active)
        self.glassChanged.emit()

    def attach_window(self, window):
        self._window = window

    @Slot()
    def startSystemMove(self):
        # Python can call QWindow.startSystemMove directly (native drag
        # with Aero snap); QML cannot invoke it, and the manual
        # position math proved unreliable.
        window = self._window
        if window is not None:
            try:
                window.startSystemMove()
            except Exception:
                pass

    # -- coordinator events --------------------------------------------

    def _on_phase(self, phase):
        self._phase = phase
        self.phaseChanged.emit()

    def _on_connected(self, connected):
        self._connected = connected
        self.connectedChanged.emit()

    def _on_running(self, running):
        self._running = running
        self.runningChanged.emit()

    def _on_accepted(self):
        self._accepted += 1
        self.matchesChanged.emit()

    def _on_played(self):
        self._played += 1
        self.matchesChanged.emit()

    def _on_result(self, result):
        self._vm.apply_game_result(result)
        self._save_all()
        self.statsChanged.emit()
        self.historyChanged.emit()

    def _on_correction(self, result):
        self._vm.apply_correction(result)
        self._save_all()
        self.statsChanged.emit()
        self.historyChanged.emit()

    def _save_all(self):
        session_store.save_session(self._vm.session, self._session_file)
        history_store.save_history(
            self._vm.history, self._history_file, self._max_history)

    def _tick(self):
        self._elapsed += 1
        self.elapsedChanged.emit()

    # -- slots (QML intents) -------------------------------------------

    @Slot()
    def toggleService(self):
        self._coordinator.toggle_service()

    @Slot()
    def startService(self):
        self._coordinator.start_service()

    @Slot(bool)
    def checkForUpdates(self, manual=False):
        self._coordinator.check_for_updates(manual)

    @Slot()
    def confirmNewSession(self):
        self._vm.reset_session()
        self._elapsed = 0
        self.elapsedChanged.emit()
        self._save_all()
        self.statsChanged.emit()

    @Slot()
    def confirmClearHistory(self):
        self._vm.history = []
        history_store.save_history(
            self._vm.history, self._history_file, self._max_history)
        self.historyChanged.emit()

    @Slot(str, str)
    def beginUpdate(self, download_url, tag):
        self.updateDownloadStarted.emit()
        self._coordinator.begin_update(download_url, tag)

    @Slot(int, result=bool)
    def applyManualAdjustment(self, lp_delta):
        """Record a hand-entered LP change. True => applied."""
        outcome = self._vm.apply_manual_adjustment(int(lp_delta))
        if not outcome["handled"]:
            return False
        self._save_all()
        self.statsChanged.emit()
        self.historyChanged.emit()
        for message, level in outcome["logs"]:
            self.logMessage.emit(message, level)
        return True

    @Slot(result="QVariantList")
    def getHistory(self):
        return list(self._vm.history)
