import QtQuick
import AppTheme 1.0

// Phase pill: border + translucent fill + label all follow one colour.
// ColorAnimation on a single property gives the 200ms crossfade free.
Rectangle {
    id: pill
    property string phaseText: "Idle"
    property color pillColor: Theme.muted

    implicitWidth: 120
    implicitHeight: 34
    radius: height / 2
    color: Qt.rgba(pillColor.r, pillColor.g, pillColor.b, 0.12)
    border.width: 1
    border.color: pillColor

    Behavior on pillColor {
        ColorAnimation { duration: Theme.fadeMs; easing.type: Easing.OutCubic }
    }

    Text {
        anchors.centerIn: parent
        text: pill.phaseText
        color: pill.pillColor
        font.pixelSize: 13
        font.bold: true
    }
}
