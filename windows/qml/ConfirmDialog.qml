import QtQuick
import AppTheme 1.0

// Tiny centred confirm overlay. Shell shows it, routes accepted().
Rectangle {
    id: confirm
    signal accepted()
    signal rejected()

    property string title: "Confirm"
    property string body: ""
    property string linkLabel: ""
    property string linkUrl: ""

    anchors.fill: parent
    color: Qt.rgba(0, 0, 0, 0.6)
    visible: false
    z: 100

    function open(titleText, bodyText, linkText, linkTarget) {
        confirm.title = titleText
        confirm.body = bodyText
        confirm.linkLabel = linkText || ""
        confirm.linkUrl = linkTarget || ""
        confirm.visible = true
    }

    MouseArea {
        anchors.fill: parent
        onClicked: confirm.rejected()
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 320)
        height: box.height + 28
        color: Theme.surface2
        radius: Theme.radius
        border.width: 1
        border.color: Theme.border

        Column {
            id: box
            width: parent.width - 32
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 14
            spacing: 10
            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                text: confirm.title
                color: Theme.text
                font.pixelSize: 14
                font.bold: true
            }
            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                text: confirm.body
                color: Theme.muted
                font.pixelSize: 12
            }
            Row {
                width: parent.width
                spacing: 8
                layoutDirection: Qt.RightToLeft
                Rectangle {
                    width: 72
                    height: 30
                    radius: 8
                    color: Theme.accent
                    Text {
                        anchors.centerIn: parent
                        text: confirm.linkUrl === "" ? "Yes" : "Update"
                        color: "white"
                        font.pixelSize: 12
                        font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: { confirm.visible = false; confirm.accepted(); }
                    }
                }
                Rectangle {
                    width: 72
                    height: 30
                    radius: 8
                    visible: confirm.linkUrl !== ""
                    color: "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: confirm.linkLabel
                        color: Theme.info
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            confirm.visible = false
                            Qt.openUrlExternally(confirm.linkUrl)
                        }
                    }
                }
                Rectangle {
                    width: 72
                    height: 30
                    radius: 8
                    color: Theme.surface
                    border.width: 1
                    border.color: Theme.border
                    Text {
                        anchors.centerIn: parent
                        text: "No"
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: confirm.rejected()
                    }
                }
            }
        }
    }

    onRejected: confirm.visible = false
}
