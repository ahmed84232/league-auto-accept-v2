"""Design tokens for the QML shell (spec v1).

Single change point for colours, radii, motion and the phase table.
QML theme values in windows/qml/AppTheme mirror these — never hardcode
a colour or duration elsewhere.
"""

WINDOW_WIDTH = 500
WINDOW_HEIGHT = 800
CONTENT_MARGIN = 16
CARD_RADIUS = 16

TITLE_BAR_HEIGHT = 32
LOG_VIEW_HEIGHT = 180

# Motion: linear-to-ease-out only, no overshoot (spec).
PHASE_FADE_MS = 200
NUMBER_ROLL_MS = 200
TAB_FADE_MS = 200

# Primary button gradients: START indigo->purple, STOP coral->crimson.
BTN_START_FROM = "#6d5df6"
BTN_START_TO = "#a855f7"
BTN_STOP_FROM = "#ef4444"
BTN_STOP_TO = "#b91c1c"

AMBER = "#f59e0b"

# Incoming phase string -> (pill label, colour hex).
# Covers LCU phases plus worker states ("Searching...", "Stopped", "None").
PHASES = {
    "Lobby": ("Lobby", "#6d5df6"),
    "Matchmaking": ("Searching...", "#f59e0b"),
    "ReadyCheck": ("Match Found!", "#3ddc97"),
    "ChampSelect": ("Champion Select", "#b388ff"),
    "GameStart": ("In Game", "#ff6b6b"),
    "InProgress": ("In Game", "#ff6b6b"),
    "InGame": ("In Game", "#ff6b6b"),
    "Reconnect": ("In Game", "#ff6b6b"),
    "Searching...": ("Client off", "#8a89a0"),
    "Stopped": ("Stopped", "#8a89a0"),
    "None": ("Idle", "#8a89a0"),
}

IDLE_PHASE = ("Idle", "#8a89a0")


def phase_style(phase):
    """Return (label, colour) for any phase string; unknown -> idle grey."""
    return PHASES.get(phase, IDLE_PHASE)
