import QtQuick
import AppTheme 1.0

// Two flat options, sliding gradient underline (~200ms).
Item {
    id: bar
    signal currentChanged(int index)
    property int selected: 0
    property var labels: ["Activity", "LP History"]

    onSelectedChanged: bar.currentChanged(bar.selected)

    implicitHeight: 36

    Row {
        id: row
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: parent.height - 2
        spacing: 4

        Repeater {
            model: bar.labels
            delegate: Rectangle {
                width: (row.width - row.spacing) / 2
                height: row.height
                radius: 8
                color: index === bar.selected ? Theme.surface2 : "transparent"
                Behavior on color {
                    ColorAnimation { duration: Theme.fadeMs }
                }
                Text {
                    anchors.centerIn: parent
                    text: modelData
                    color: (index === bar.selected || hoverArea.containsMouse) ? Theme.text : Theme.muted
                    font.pixelSize: 12
                    font.bold: true
                    Behavior on color {
                        ColorAnimation { duration: Theme.fadeMs }
                    }
                }
                MouseArea {
                    id: hoverArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (bar.selected !== index) {
                            bar.selected = index
                        }
                    }
                }
            }
        }
    }

    Item {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 2

        Rectangle {
            id: cursor
            width: (parent.width - 4) / 2
            height: 2
            radius: 1
            x: bar.selected * (width + 4)
            gradient: Gradient {
                GradientStop { position: 0; color: Theme.accent }
                GradientStop { position: 1; color: Theme.violet }
            }
            Behavior on x {
                NumberAnimation { duration: Theme.fadeMs; easing.type: Easing.OutCubic }
            }
        }
    }
}
