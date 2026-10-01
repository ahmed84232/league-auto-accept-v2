import QtQuick
import QtQuick.Layouts
import AppTheme 1.0

// Status card: connection stack (left) + phase pill (right).
// Accepted/played footer kept (same flagged deviation as widgets).
Card {
    id: status
    implicitHeight: body.implicitHeight + 28
    property bool connected: false
    property string phaseText: "Idle"
    property color phaseColor: Theme.muted
    property int accepted: 0
    property int played: 0
    property int elapsedSecs: 0

    function fmtElapsed(s) {
        var m = Math.floor(s / 60);
        var r = s % 60;
        return ("0" + m).slice(-2) + ":" + ("0" + r).slice(-2);
    }

    Column {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 14
        spacing: 8

        RowLayout {
            width: parent.width
            spacing: 10

            // Pulse dot: opacity breathes while connected.
            Rectangle {
                id: dot
                Layout.preferredWidth: 12
                Layout.preferredHeight: 12
                Layout.alignment: Qt.AlignVCenter
                radius: 6
                color: status.connected ? Theme.success : Theme.error
                opacity: 1.0

                // While running, the animation owns opacity; when it
                // stops the binding snaps back to 1.0 — never frozen dim.
                SequentialAnimation on opacity {
                    id: pulse
                    running: status.connected
                    loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 0.45; duration: 700; easing.type: Easing.InOutQuad }
                    NumberAnimation { from: 0.45; to: 1.0; duration: 700; easing.type: Easing.InOutQuad }
                }
            }

            Column {
                spacing: 0
                Layout.alignment: Qt.AlignVCenter
                Text {
                    text: status.connected ? "Connected to League Client" : "Disconnected"
                    color: Theme.text
                    font.pixelSize: 13
                    font.bold: true
                }
                Text {
                    text: "SESSION " + status.fmtElapsed(status.elapsedSecs)
                    color: Theme.muted
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }

            PhasePill {
                Layout.alignment: Qt.AlignVCenter
                phaseText: status.phaseText
                pillColor: status.phaseColor
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.border
        }

        Text {
            text: "ACCEPTED " + status.accepted + "  ·  PLAYED " + status.played
            color: Theme.muted
            font.pixelSize: 10
            font.bold: true
        }
    }
}
