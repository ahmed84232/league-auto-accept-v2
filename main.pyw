import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from client_api.app_paths import INSTANCE_LOCK_FILE
from client_api.single_instance import ensure_single_instance
from windows.qml_shell import run_qml


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    guard = ensure_single_instance(INSTANCE_LOCK_FILE)
    if guard is None:
        QMessageBox.warning(
            None,
            "League Auto-Accept",
            "It's already running — check your taskbar.",
        )
        return
    app._instance_guard = guard  # keep the lock for the whole process

    # Old shortcuts may still pass --qml/--widgets; QML is now the only
    # shell, so strip them for backward compatibility.
    remaining = [a for a in sys.argv if a not in ("--qml", "--widgets")]
    sys.exit(run_qml(remaining))


if __name__ == "__main__":
    main()
