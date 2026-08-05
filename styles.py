PALETTE = {
    "BG": "#0a0a12",
    "SURFACE": "#14141f",
    "SURFACE_2": "#1d1d2a",
    "BORDER": "#2c2c41",
    "TEXT": "#eceaf3",
    "MUTED": "#8a89a0",
    "ACCENT": "#6d5df6",
    "ACCENT_LIGHT": "#8a7dff",
    "ACCENT_DARK": "#5a4ae0",
    "VIOLET": "#a855f7",
    "SUCCESS": "#3ddc97",
    "WARNING": "#ffb454",
    "ERROR": "#ff6b6b",
    "INFO": "#64b5f6",
    "CHAMP": "#b388ff",
}

LOG_COLORS = {
    "info": PALETTE["INFO"],
    "success": PALETTE["SUCCESS"],
    "warning": PALETTE["WARNING"],
    "error": PALETTE["ERROR"],
}

_QSS_TEMPLATE = """
* {
    font-family: 'Segoe UI Variable', 'Segoe UI', Arial, sans-serif;
}

QMainWindow#MainWindow {
    background-color: {{BG}};
}

QWidget {
    background-color: transparent;
    color: {{TEXT}};
    font-size: 13px;
}

#titleBar {
    background-color: {{SURFACE}};
    border-bottom: 1px solid {{BORDER}};
}

#appDot {
    color: {{ACCENT}};
    font-size: 12px;
}

#appTitle {
    font-size: 13px;
    font-weight: 600;
    color: {{TEXT}};
    letter-spacing: 0.3px;
}

#windowBtn {
    background-color: transparent;
    color: {{MUTED}};
    border: none;
    border-radius: 7px;
    font-size: 14px;
}

#windowBtn:hover {
    background-color: {{SURFACE_2}};
    color: {{TEXT}};
}

#windowBtnClose {
    background-color: transparent;
    color: {{MUTED}};
    border: none;
    border-radius: 7px;
    font-size: 14px;
}

#windowBtnClose:hover {
    background-color: {{ERROR}};
    color: #ffffff;
}

#card {
    background-color: {{SURFACE}};
    border: 1px solid {{BORDER}};
    border-radius: 16px;
}

#divider {
    background-color: {{BORDER}};
}

#connectionDot {
    font-size: 12px;
    color: {{ERROR}};
}

#connectionDot[state="connected"] {
    color: {{SUCCESS}};
}

#connectionLabel {
    font-size: 13px;
    font-weight: 600;
    color: {{TEXT}};
}

#matchesValue {
    font-size: 22px;
    font-weight: 700;
    color: {{TEXT}};
}

#matchesLabel {
    font-size: 10px;
    font-weight: 600;
    color: {{MUTED}};
    letter-spacing: 1.2px;
}

#sectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: {{MUTED}};
    letter-spacing: 1.2px;
}

#phaseBadge {
    background-color: rgba(255, 255, 255, 0.04);
    color: {{MUTED}};
    border: 1px solid {{BORDER}};
    border-radius: 12px;
    padding: 10px 22px;
    font-size: 15px;
    font-weight: 600;
}

#phaseBadge[phase="searching"] {
    background-color: rgba(100, 181, 246, 0.10);
    border-color: rgba(100, 181, 246, 0.5);
    color: {{INFO}};
}

#phaseBadge[phase="lobby"] {
    background-color: rgba(109, 93, 246, 0.10);
    border-color: rgba(109, 93, 246, 0.5);
    color: {{ACCENT_LIGHT}};
}

#phaseBadge[phase="matchmaking"] {
    background-color: rgba(255, 180, 84, 0.10);
    border-color: rgba(255, 180, 84, 0.5);
    color: {{WARNING}};
}

#phaseBadge[phase="readycheck"] {
    background-color: rgba(61, 220, 151, 0.10);
    border-color: rgba(61, 220, 151, 0.5);
    color: {{SUCCESS}};
}

#phaseBadge[phase="champselect"] {
    background-color: rgba(179, 136, 255, 0.10);
    border-color: rgba(179, 136, 255, 0.5);
    color: {{CHAMP}};
}

#phaseBadge[phase="ingame"] {
    background-color: rgba(255, 107, 107, 0.10);
    border-color: rgba(255, 107, 107, 0.5);
    color: {{ERROR}};
}

#logHeader {
    font-size: 11px;
    font-weight: 600;
    color: {{MUTED}};
    letter-spacing: 1.2px;
}

#clearButton {
    background-color: {{SURFACE_2}};
    color: {{MUTED}};
    border: 1px solid {{BORDER}};
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 12px;
}

#clearButton:hover {
    background-color: {{BORDER}};
    color: {{TEXT}};
}

#logEntry {
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 6px;
}

QScrollArea, QScrollArea > QWidget > QWidget {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background-color: {{BORDER}};
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: {{SURFACE_2}};
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background-color: transparent;
}

#primaryButton {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 {{ACCENT}}, stop: 1 {{VIOLET}});
    color: #ffffff;
    border: none;
    border-radius: 14px;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 16px;
}

#primaryButton:hover {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 {{ACCENT_LIGHT}}, stop: 1 #b46aff);
}

#primaryButton:pressed {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 {{ACCENT_DARK}}, stop: 1 #8f45d8);
}

#primaryButton[state="stop"] {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #e04848, stop: 1 #c2375f);
}

#primaryButton[state="stop"]:hover {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #f05555, stop: 1 #d3416b);
}

#primaryButton[state="stop"]:pressed {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #c23a3a, stop: 1 #a82e52);
}

#hint {
    color: {{MUTED}};
    font-size: 11px;
}
"""

STYLESHEET = _QSS_TEMPLATE
for _key, _value in PALETTE.items():
    STYLESHEET = STYLESHEET.replace("{{" + _key + "}}", _value)
