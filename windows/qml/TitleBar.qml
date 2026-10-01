import QtQuick
import AppTheme 1.0

// 32px frameless chrome: drag-to-move, mini logo, min/close.
// Double-click is inert (spec: no maximise toggle).
Rectangle {
    id: chrome
    signal minimiseRequested()
    signal closeRequested()

    height: 32
    color: Theme.surface

    // Mini logo: gradient tile.
    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 16
        width: 12
        height: 12
        radius: 3
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.accent }
            GradientStop { position: 1; color: Theme.violet }
        }
    }

    Text {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 34
        text: "League Auto-Accept"
        color: Theme.muted
        font.pixelSize: 12
    }

    Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: 6
        spacing: 2

        Repeater {
            model: [
                {label: "—", action: "min"},
                {label: "✕", action: "close"}
            ]
            delegate: Rectangle {
                width: 36
                height: 24
                radius: 7
                color: hover.hovered
                    ? (modelData.action === "close" ? Theme.error : Theme.surface2)
                    : "transparent"
                Behavior on color { ColorAnimation { duration: 120 } }
                Text {
                    anchors.centerIn: parent
                    text: modelData.label
                    color: hover.hovered && modelData.action === "close" ? "white" : Theme.muted
                    font.pixelSize: 13
                }
                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (modelData.action === "close") chrome.closeRequested()
                        else chrome.minimiseRequested()
                    }
                }
            }
        }
    }

    // Native system drag via the bridge (Aero snap included).
    // QML cannot invoke QWindow.startSystemMove itself, and manual
    // position math proved unreliable — so Python does this one call.
    // Double-click inert per spec.
    MouseArea {
        anchors.fill: parent
        z: -1
        onPressed: bridge.startSystemMove()
        onDoubleClicked: {}
    }
}
