"""QML entry point (the only UI shell).

Composition root for the QML shell: loads stores, builds the session
manager + coordinator, bridges them to QML.
"""

import os

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine

from client_api import history_store, session_store
from client_api.app_paths import APP_DIR, HISTORY_FILE, SESSION_FILE
from client_api.session_manager import SessionManager
from version import __version__
from windows.coordinator import ServiceCoordinator
from windows.qml_bridge import QmlBridge

OWNER = "ahmed84232"
REPO = "league-auto-accept-v2"
MAX_HISTORY = 200


def run_qml(argv):
    # main.pyw usually owns the QApplication already (single-instance
    # guard lives there); fall back to our own only when run standalone.
    app = QApplication.instance() or QApplication(argv)

    session = session_store.load_session(SESSION_FILE)
    history = history_store.load_history(HISTORY_FILE, MAX_HISTORY)
    vm = SessionManager(session, history, {}, MAX_HISTORY)
    coordinator = ServiceCoordinator(OWNER, REPO, __version__)
    bridge = QmlBridge(coordinator, vm, SESSION_FILE, HISTORY_FILE, MAX_HISTORY)
    coordinator.check_for_updates()

    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(APP_DIR, "windows", "qml"))
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.rootContext().setContextProperty("appVersion", __version__)
    engine.load(os.path.join(APP_DIR, "windows", "qml", "Main.qml"))

    if not engine.rootObjects():
        raise RuntimeError("QML shell failed to load")
    root = engine.rootObjects()[0]
    bridge.attach_window(root)

    from PySide6.QtCore import QCoreApplication
    for _ in range(20):
        QCoreApplication.processEvents()

    try:
        from windows.glass import enable_glass
        bridge.set_glass_active(enable_glass(engine.rootObjects()[0]))
    except Exception:
        pass

    code = app.exec()
    coordinator.shutdown()
    return code
