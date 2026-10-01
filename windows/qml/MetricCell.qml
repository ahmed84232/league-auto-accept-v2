import QtQuick
import AppTheme 1.0

// One metric cell: rolling number over a small-caps caption.
// Root is a plain Item (NOT a Column positioner): positioners ignore
// Layout.fillWidth, which squeezed narrow columns and spread wide ones.
// The roll is a plain Behavior — no timers, no threads.
Item {
    id: cell
    implicitHeight: body.implicitHeight

    property int target: 0
    property int shown: 0
    property string caption: ""
    property color valueColor: Theme.text
    property var formatter: function (v) { return v.toString(); }

    Behavior on shown {
        id: roll
        NumberAnimation { duration: Theme.rollMs; easing.type: Easing.OutCubic }
    }
    onTargetChanged: cell.shown = cell.target
    Component.onCompleted: {
        roll.enabled = false
        cell.shown = cell.target
        roll.enabled = true
    }

    Column {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 4

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: cell.formatter(cell.shown)
            color: cell.valueColor
            font.family: Theme.fontMono
            font.pixelSize: 28
            font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: cell.caption.toUpperCase()
            color: Theme.muted
            font.pixelSize: 10
            font.bold: true
        }
    }
}
