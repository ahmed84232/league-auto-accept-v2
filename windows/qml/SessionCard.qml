import QtQuick
import QtQuick.Layouts
import AppTheme 1.0

// Session metrics: 2x2 rolling counters + centred rank row.
// Emits newSessionRequested / fixLpRequested — shell owns the dialogs.
Card {
    id: session
    implicitHeight: body.implicitHeight + 28
    signal newSessionRequested()
    signal fixLpRequested()

    property int wins: 0
    property int losses: 0
    property int remakes: 0
    property int netLp: 0
    property string rankTitle: "Unranked"
    property string rankLp: ""

    Column {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 14
        spacing: 10

        RowLayout {
            width: parent.width
            Text {
                text: "SESSION STATS"
                color: Theme.muted
                font.pixelSize: 11
                font.bold: true
            }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }
            Rectangle {
                id: newBtn
                Layout.preferredWidth: 92
                Layout.preferredHeight: 28
                radius: 8
                color: btnArea.containsMouse ? Theme.border : Theme.surface2
                border.width: 1
                border.color: Theme.border
                Text {
                    anchors.centerIn: parent
                    text: "New Session"
                    color: Theme.muted
                    font.pixelSize: 12
                }
                MouseArea {
                    id: btnArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: session.newSessionRequested()
                }
            }
            Rectangle {
                Layout.preferredWidth: 64
                Layout.preferredHeight: 28
                radius: 8
                color: fixArea.containsMouse ? Theme.border : Theme.surface2
                border.width: 1
                border.color: Theme.border
                Text {
                    anchors.centerIn: parent
                    text: "Fix LP"
                    color: Theme.muted
                    font.pixelSize: 12
                }
                MouseArea {
                    id: fixArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: session.fixLpRequested()
                }
            }
        }

        GridLayout {
            width: parent.width
            columns: 4
            columnSpacing: 8
            rowSpacing: 8
            MetricCell {
                Layout.fillWidth: true
                target: session.wins
                caption: "Wins"
                valueColor: Theme.success
            }
            MetricCell {
                Layout.fillWidth: true
                target: session.losses
                caption: "Losses"
                valueColor: Theme.error
            }
            MetricCell {
                Layout.fillWidth: true
                target: session.remakes
                caption: "Remakes"
                valueColor: Theme.muted
            }
            MetricCell {
                Layout.fillWidth: true
                target: session.netLp
                caption: "Net LP"
                valueColor: session.netLp > 0 ? Theme.success : session.netLp < 0 ? Theme.error : Theme.muted
                formatter: function (v) { return (v >= 0 ? "+" : "") + v; }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.border
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8
            Text {
                id: rankText
                text: session.rankTitle
                color: Theme.accentLight
                font.pixelSize: 15
                font.bold: true
            }
            Text {
                anchors.baseline: rankText.baseline
                text: session.rankLp
                color: Theme.muted
                font.pixelSize: 13
                font.bold: true
            }
        }
    }
}
