import QtQuick
import AppTheme 1.0

// Primary action: gradient swaps START (indigo) ⇄ STOP (coral)
// while the label toggles instantly. Stopping halts the worker;
// session data is untouched (New Session owns that).
Rectangle {
    id: btn
    signal clicked()

    property bool running: false
    property color from: Theme.accent
    property color to: Theme.violet

    implicitHeight: 56
    radius: 14

    Behavior on from { ColorAnimation { duration: 200 } }
    Behavior on to { ColorAnimation { duration: 200 } }
    onRunningChanged: {
        if (btn.running) {
            btn.from = Theme.stopFrom
            btn.to = Theme.stopTo
        } else {
            btn.from = Theme.accent
            btn.to = Theme.violet
        }
    }

    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { position: 0; color: btn.pressedShade(btn.from) }
        GradientStop { position: 1; color: btn.pressedShade(btn.to) }
    }

    function pressedShade(c) {
        if (pressArea.pressed) return Qt.darker(c, 1.25);
        if (pressArea.containsMouse) return Qt.lighter(c, 1.08);
        return c;
    }

    Text {
        anchors.centerIn: parent
        text: btn.running ? "STOP" : "START"
        color: "white"
        font.pixelSize: 13
        font.bold: true
    }

    MouseArea {
        id: pressArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: btn.clicked()
    }
}
