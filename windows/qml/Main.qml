import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import AppTheme 1.0

Window {
    id: root
    width: Theme.winW
    height: Theme.winH
    minimumWidth: Theme.winW
    maximumWidth: Theme.winW
    minimumHeight: Theme.winH
    maximumHeight: Theme.winH
    visible: true
    color: bridge.glassActive ? "transparent" : Theme.canvas
    // Full hint set: frameless look, but a real taskbar entry with
    // minimise/restore, Alt+Tab and taskbar-click support.
    flags: Qt.FramelessWindowHint | Qt.Window
        | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint
    title: "League Auto-Accept"

    // -- backend -> views -------------------------------------------------
    Connections {
        target: bridge
        function onLogMessage(message, level) { logView.addLog(message, level) }
        function onHistoryChanged() { historyView.refresh() }
        function onUpdateCheckFailed(manual) {
            if (manual) updateFailed.open("Update check failed",
                "Could not reach GitHub. Check your internet connection.")
        }
        function onUpdateAvailable(tag, body, url, downloadUrl) {
            pendingUrl = url
            pendingDownload = downloadUrl
            pendingTag = tag
            updateOffer.open("Update available: " + tag,
                (body || "").trim() || "No release notes.",
                downloadUrl ? "GitHub" : "", downloadUrl ? url : "")
        }
        function onUpdateUpToDate() {
            upToDate.open("Up to date",
                "You're running the latest version (v" + appVersion + ").")
        }
        function onUpdateDownloadFailed(message) { dock.downloading = false }
        function onUpdateProgressed(value) { dock.progress = value / 100 }
        function onUpdateDownloadStarted() {
            dock.downloading = true
            dock.progress = 0
        }
        function onRestartRequested() { Qt.quit() }
    }
    property string pendingUrl: ""
    property string pendingDownload: ""
    property string pendingTag: ""

    Item {
        anchors.fill: parent

        // Chrome with native-feel drag + min/close.
        TitleBar {
            width: parent.width
            onMinimiseRequested: root.showMinimized()
            onCloseRequested: root.close()
        }

        ColumnLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 44
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 16
            anchors.leftMargin: Theme.margin
            anchors.rightMargin: Theme.margin
            spacing: 14

            StatusCard {
                Layout.fillWidth: true
                connected: bridge.connected
                phaseText: bridge.phaseLabel
                phaseColor: bridge.phaseColor
                accepted: bridge.accepted
                played: bridge.played
                elapsedSecs: bridge.elapsedSecs
            }

            SessionCard {
                Layout.fillWidth: true
                wins: bridge.wins
                losses: bridge.losses
                remakes: bridge.remakes
                netLp: bridge.netLp
                rankTitle: bridge.rankTitle
                rankLp: bridge.rankLp
                onNewSessionRequested: confirm.open(
                    "New Session",
                    "Start a new session? Current wins/losses/remakes and LP change will be cleared.")
                onFixLpRequested: lpAdjust.open()
            }

            SegmentedTabs {
                objectName: "tabs"
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                onCurrentChanged: function (index) {
                    logView.visible = index === 0
                    historyView.visible = index === 1
                }
            }

            LogView {
                id: logView
                objectName: "logView"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 200
            }
            HistoryView {
                id: historyView
                objectName: "historyView"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 200
                visible: false
                Component.onCompleted: historyView.refresh()
                onClearRequested: confirmClear.open(
                    "Clear history",
                    "Delete the saved LP match history?")
            }

            ActionDock {
                id: dock
                objectName: "dock"
                Layout.fillWidth: true
                running: bridge.running
                connected: bridge.connected
                version: appVersion
                onStartStop: bridge.toggleService()
                onCheckUpdates: bridge.checkForUpdates(true)
            }
        }
    }

    ConfirmDialog {
        id: confirm
        onAccepted: bridge.confirmNewSession()
    }
    LpAdjustDialog {
        id: lpAdjust
        onApplied: function (delta) { bridge.applyManualAdjustment(delta) }
    }
    ConfirmDialog {
        id: confirmClear
        onAccepted: bridge.confirmClearHistory()
    }
    ConfirmDialog {
        id: updateOffer
        onAccepted: {
            dock.downloading = true
            dock.progress = 0
            bridge.beginUpdate(root.pendingDownload, root.pendingTag)
        }
    }
    ConfirmDialog {
        id: updateFailed
    }
    ConfirmDialog {
        id: upToDate
    }
}
