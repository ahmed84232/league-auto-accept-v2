"""Windows 11 glass (Mica) + immersive dark mode via DWM.

Best-effort only: returns True when the backdrop was applied, False on
anything older/different — callers keep the opaque canvas fallback.
QML binds root translucency to bridge.glassActive, so a silent DWM
failure can never produce a half-transparent window.
"""

import ctypes
import sys

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_MICA_EFFECT = 1029
DWMWA_SYSTEMBACKDROP_TYPE = 38

# DWMWA_SYSTEMBACKDROP_TYPE values
DWMSBT_AUTO = 0
DWMSBT_MICA = 2


def _set_attr(hwnd, attr, value):
    try:
        dwmapi = ctypes.windll.dwmapi
    except (AttributeError, OSError):
        return False
    val = ctypes.c_int(value)
    try:
        return dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(int(hwnd)),
            ctypes.c_uint(attr),
            ctypes.byref(val),
            ctypes.sizeof(val),
        ) == 0
    except OSError:
        return False


def _extend_frame(hwnd):
    """Extend the glass frame into the client area (required, else black)."""
    try:
        dwmapi = ctypes.windll.dwmapi
    except (AttributeError, OSError):
        return False
    margins = (ctypes.c_int * 4)(-1, -1, -1, -1)
    try:
        return dwmapi.DwmExtendFrameIntoClientArea(
            ctypes.c_void_p(int(hwnd)), margins) == 0
    except OSError:
        return False


def enable_glass(window):
    """Apply dark mode + Mica to a shown top-level window. Returns bool."""
    if sys.platform != "win32":
        return False
    try:
        build = sys.getwindowsversion().build
    except AttributeError:
        return False
    if build < 22000:  # pre-Windows 11: no Mica
        return False
    try:
        hwnd = int(window.winId())
    except (AttributeError, TypeError):
        return False
    if not hwnd:
        return False
    _set_attr(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 1)
    if not _extend_frame(hwnd):
        return False
    if build >= 22523:
        return _set_attr(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_MICA)
    return _set_attr(hwnd, DWMWA_MICA_EFFECT, 1)
