import QtQuick
import QtQuick.Layouts
import AppTheme 1.0

// Activity console: monospace feed, at least 180px tall (spec), growing
// with the page so both tabs fill identically — no jump on switch.
// Append-only from bridge.logMessage; Clear is view-local (as before).
Card {
    id: log
    clip: true

    function levelColor(l) {
        if (l === "success") return Theme.success;
        if (l === "warning") return Theme.warning;
        if (l === "error") return Theme.error;
        return Theme.info;
    }
    function levelIcon(l) {
        if (l === "success") return "✓";
        if (l === "warning") return "▲";
        if (l === "error") return "✕";
        return "●";
    }
    function stamp() {
        var d = new Date();
        var p = function (n) { return ("0" + n).slice(-2); };
        return p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
    }
    function esc(s) {
        return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
                         .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
    function addLog(message, level) {
        feed.append({time: stamp(), icon: levelIcon(level),
                     msg: esc(message), color: levelColor(level)});
        // Settle, then pin to the bottom.
        bottomTimer.restart();
    }
    function clear() {
        feed.clear();
    }

    Timer {
        id: bottomTimer
        interval: 0
        onTriggered: feedView.positionViewAtEnd()
    }

    ListModel { id: feed }

    Column {
        id: topPart
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 8

        RowLayout {
            width: parent.width
            Text {
                text: "ACTIVITY LOG"
                color: Theme.muted
                font.pixelSize: 11
                font.bold: true
            }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }
            Rectangle {
                Layout.preferredWidth: 64
                Layout.preferredHeight: 26
                radius: 8
                color: clearArea.containsMouse ? Theme.border : Theme.surface2
                border.width: 1
                border.color: Theme.border
                Text {
                    anchors.centerIn: parent
                    text: "Clear"
                    color: Theme.muted
                    font.pixelSize: 12
                }
                MouseArea {
                    id: clearArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: log.clear()
                }
            }
        }
    }

    ListView {
        id: feedView
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: topPart.bottom
        anchors.margins: 12
        anchors.topMargin: 8
        clip: true
        model: feed
        spacing: 2
            delegate: Text {
                width: feedView.width - 6
                wrapMode: Text.WordWrap
                textFormat: Text.RichText
                font.family: Theme.fontMono
                font.pixelSize: 12
            text: "<font color=\"" + Theme.muted + "\">" + time + "</font>"
                  + "  <font color=\"" + color + "\">" + icon + "</font>"
                  + "  <font color=\"" + Theme.text + "\">" + msg + "</font>"
        }
    }
}
