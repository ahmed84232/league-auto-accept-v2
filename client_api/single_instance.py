"""Single-instance guard (no backend deps beyond Qt).

Holds a lock file for the life of the process. A second launch finds
the lock held by a live process and exits with a message instead of
starting a duplicate auto-accept worker. Stale locks from crashes are
reclaimed automatically (dead pid = free lock).
"""

from PySide6.QtCore import QLockFile


class SingleInstance:
    def __init__(self, lock_path):
        self._lock = QLockFile(lock_path)
        # A crashed previous run may leave a stale file; a zero stale
        # window reaps it immediately when its pid is dead.
        self._lock.setStaleLockTime(0)

    def try_acquire(self):
        """True when this process is the single instance (lock now held)."""
        return self._lock.tryLock(0)

    def release(self):
        try:
            self._lock.unlock()
        except RuntimeError:
            pass


def ensure_single_instance(lock_path):
    """Return a held guard, or None when another live instance owns it."""
    guard = SingleInstance(lock_path)
    return guard if guard.try_acquire() else None
