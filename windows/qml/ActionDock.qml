import QtQuick
import QtQuick.Layouts
import AppTheme 1.0

// Sticky action dock: morphing button + download progress + metadata.
// Emits intents; the bridge + shell own dialogs and flow.
Column {
    id: dock
    spacing: 8

    property bool running: false
    property bool connected: false
    property string version: ""
    property bool downloading: false
    property real progress: 0

    signal startStop()
    signal checkUpdates()

    ButtonMorph {
        width: parent.width
        running: dock.running
        onClicked: dock.startStop()
    }

    Rectangle {
        width: parent.width
        height: 8
        radius: 4
        color: Theme.surface2
        border.width: 1
        border.color: Theme.border
        visible: dock.downloading
        Rectangle {
            width: parent.width * dock.progress
            height: parent.height
            radius: 4
            color: Theme.accent
        }
    }

    RowLayout {
        width: parent.width
        Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }
        Text {
            text: ("V" + dock.version + " // " + (dock.connected ? "Connected" : "Disconnected")).toUpperCase()
            color: Theme.muted
            font.pixelSize: 10
            font.bold: true
        }
        Text {
            text: "Check for updates"
            color: Theme.info
            font.pixelSize: 12
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: dock.checkUpdates()
            }
        }
        Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }
    }
}
