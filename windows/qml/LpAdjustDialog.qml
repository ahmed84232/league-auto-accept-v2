import QtQuick
import AppTheme 1.0

// Manual LP fix: type a signed number, see the outcome live, apply.
// Positive counts a win, negative a loss (late Riot adjustments etc.).
Rectangle {
    id: adjust
    signal applied(int delta)
    signal rejected()

    anchors.fill: parent
    color: Qt.rgba(0, 0, 0, 0.6)
    visible: false
    z: 100

    function open() {
        field.text = ""
        adjust.visible = true
        field.forceActiveFocus()
    }

    function currentValue() {
        var v = parseInt(field.text, 10)
        return isNaN(v) ? 0 : v
    }

    MouseArea {
        anchors.fill: parent
        onClicked: adjust.rejected()
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 300)
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
                text: "Fix LP"
                color: Theme.text
                font.pixelSize: 14
                font.bold: true
            }
            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "LP change to record (+win / −loss, e.g. 17 or -12):"
                color: Theme.muted
                font.pixelSize: 12
            }
            Rectangle {
                width: parent.width
                height: 36
                radius: 8
                color: Theme.surface
                border.width: 1
                border.color: field.activeFocus ? Theme.accent : Theme.border
                TextInput {
                    id: field
                    anchors.fill: parent
                    anchors.margins: 8
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.text
                    font.family: Theme.fontMono
                    font.pixelSize: 16
                    font.bold: true
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: -100; top: 100 }
                    onAccepted: {
                        if (adjust.currentValue() !== 0) {
                            adjust.visible = false
                            adjust.applied(adjust.currentValue())
                        }
                    }
                }
            }
            Text {
                width: parent.width
                text: {
                    var v = adjust.currentValue()
                    if (v === 0) return "Enter a non-zero number"
                    return (v > 0 ? "Counts as WIN " : "Counts as LOSS ")
                        + (v > 0 ? "+" : "") + v + " LP"
                }
                color: {
                    var v = adjust.currentValue()
                    if (v === 0) return Theme.muted
                    return v > 0 ? Theme.success : Theme.error
                }
                font.pixelSize: 12
                font.bold: true
            }
            Row {
                width: parent.width
                spacing: 8
                layoutDirection: Qt.RightToLeft
                Rectangle {
                    width: 72
                    height: 30
                    radius: 8
                    color: adjust.currentValue() === 0 ? Theme.surface : Theme.accent
                    Text {
                        anchors.centerIn: parent
                        text: "Apply"
                        color: "white"
                        font.pixelSize: 12
                        font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (adjust.currentValue() !== 0) {
                                adjust.visible = false
                                adjust.applied(adjust.currentValue())
                            }
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
                        text: "Cancel"
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: adjust.rejected()
                    }
                }
            }
        }
    }

    onRejected: adjust.visible = false
}
