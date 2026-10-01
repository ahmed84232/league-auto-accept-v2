pragma Singleton
import QtQuick

QtObject {
    // Canvas + surfaces (spec Layer 0-2)
    readonly property color canvas: "#0a0a12"
    readonly property color surface: "#14141f"
    readonly property color surface2: "#1d1d2a"
    readonly property color border: "#2c2c41"
    readonly property color text: "#eceaf3"
    readonly property color muted: "#8a89a0"
    // Accents
    readonly property color accent: "#6d5df6"
    readonly property color accentLight: "#8a7dff"
    readonly property color violet: "#a855f7"
    readonly property color success: "#3ddc97"
    readonly property color error: "#ff6b6b"
    readonly property color warning: "#ffb454"
    readonly property color info: "#64b5f6"
    readonly property color amber: "#f59e0b"
    readonly property color champ: "#b388ff"
    readonly property color stopFrom: "#ef4444"
    readonly property color stopTo: "#b91c1c"
    // Geometry
    readonly property int winW: 500
    readonly property int winH: 800
    readonly property int margin: 16
    readonly property int radius: 16
    // Motion (ms, ease-out only)
    readonly property int fadeMs: 200
    readonly property int rollMs: 200
    // Fonts
    readonly property string fontUi: "Segoe UI Variable, Segoe UI"
    readonly property string fontMono: "Cascadia Code, Consolas"
}
