import QtQuick
import QtQuick.Layouts
import AppTheme 1.0

// LP history: cumulative chart + entry list.
// Pure renderer over bridge.getHistory(); Clear asks the shell to confirm.
Card {
    id: history
    signal clearRequested()
    clip: true

    function fmtDate(iso) {
        var d = new Date(iso);
        if (isNaN(d.getTime())) return "—";
        var p = function (n) { return ("0" + n).slice(-2); };
        return p(d.getDate()) + "/" + p(d.getMonth() + 1) + "/" + d.getFullYear();
    }
    function rowColor(result, delta) {
        if (result === "remake" || delta === null || delta === undefined)
            return Theme.muted;
        if (delta > 0) return Theme.success;
        if (delta < 0) return Theme.error;
        return Theme.muted;
    }
    function rowLetter(result) {
        if (result === "win") return "W";
        if (result === "loss") return "L";
        if (result === "remake") return "R";
        return "?";
    }
    function rowWord(result) {
        if (result === "win") return "WIN";
        if (result === "loss") return "LOSS";
        if (result === "remake") return "REMAKE";
        return "GAME";
    }
    // Cumulative curve as 0..1 points; remakes (null) hold flat.
    property var curve: []
    property real zeroY: 0.5

    function refresh() {
        var games = bridge.getHistory();
        rows.clear();
        for (var i = games.length - 1; i >= 0; --i) {
            var g = games[i];
            var lp = (g.lp === null || g.lp === undefined) ? null : g.lp;
            rows.append({letter: rowLetter(g.result), word: rowWord(g.result), lp: lp,
                         date: fmtDate(g.ts), color: rowColor(g.result, lp)});
        }
        var run = 0, vals = [0];
        for (var j = 0; j < games.length; ++j) {
            var d = games[j].lp;
            if (d !== null && d !== undefined) run += d;
            vals.push(run);
        }
        var lo = 0, hi = 0, k;
        for (k = 0; k < vals.length; ++k) {
            if (vals[k] < lo) lo = vals[k];
            if (vals[k] > hi) hi = vals[k];
        }
        var span = Math.max(1, hi - lo);
        lo -= span * 0.15;
        hi += span * 0.15;
        var pts = [];
        for (k = 0; k < vals.length; ++k) {
            pts.push({x: vals.length < 2 ? 0 : k / (vals.length - 1),
                      y: 1 - (vals[k] - lo) / (hi - lo)});
        }
        zeroY = 1 - (0 - lo) / (hi - lo);
        curve = pts;
        spark.requestPaint();
    }

    ListModel { id: rows }

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
                text: "LP HISTORY"
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
                    onClicked: history.clearRequested()
                }
            }
        }

        Item { width: 1; height: 4 }

        Canvas {
            id: spark
            width: parent.width
            height: 84
            onPaint: {
                var ctx = getContext("2d");
                ctx.clearRect(0, 0, width, height);
                var pts = history.curve;
                // zero line
                ctx.strokeStyle = Theme.border;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, history.zeroY * height);
                ctx.lineTo(width, history.zeroY * height);
                ctx.stroke();
                if (pts.length < 2) return;
                var px = function (p) { return p.x * width; };
                var py = function (p) { return p.y * height; };
                // area fill
                var grad = ctx.createLinearGradient(0, 0, 0, height);
                grad.addColorStop(0, Qt.rgba(Theme.accentLight.r, Theme.accentLight.g, Theme.accentLight.b, 0.30));
                grad.addColorStop(1, Qt.rgba(Theme.accentLight.r, Theme.accentLight.g, Theme.accentLight.b, 0.0));
                ctx.beginPath();
                ctx.moveTo(px(pts[0]), height);
                for (var i = 0; i < pts.length; ++i) ctx.lineTo(px(pts[i]), py(pts[i]));
                ctx.lineTo(px(pts[pts.length - 1]), height);
                ctx.closePath();
                ctx.fillStyle = grad;
                ctx.fill();
                // curve
                ctx.strokeStyle = Theme.accentLight;
                ctx.lineWidth = 2;
                ctx.lineJoin = "round";
                ctx.beginPath();
                ctx.moveTo(px(pts[0]), py(pts[0]));
                for (var j = 1; j < pts.length; ++j) ctx.lineTo(px(pts[j]), py(pts[j]));
                ctx.stroke();
            }
        }

        Item { width: 1; height: 4 }
    }

    ListView {
        id: rowsView
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: topPart.bottom
        anchors.margins: 12
        anchors.topMargin: 0
        clip: true
        model: rows
        spacing: 0
            delegate: Item {
                width: rowsView.width
                height: row.height + 10
                Rectangle {
                    anchors.fill: parent
                    radius: 6
                    color: index % 2 === 0 ? "transparent"
                          : Qt.rgba(Theme.surface2.r, Theme.surface2.g, Theme.surface2.b, 0.6)
                }
                Row {
                    id: row
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 6
                    spacing: 8
                    Rectangle {
                        width: 18
                        height: 18
                        radius: 5
                        anchors.verticalCenter: parent.verticalCenter
                        color: Qt.rgba(model.color.r, model.color.g, model.color.b, 0.14)
                        border.width: 1
                        border.color: model.color
                        Text {
                            anchors.centerIn: parent
                            text: model.letter
                            color: model.color
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        font.family: Theme.fontMono
                        font.pixelSize: 13
                        color: model.color
                        text: model.word
                              + "  " + (model.lp == null ? "—" : (model.lp >= 0 ? "+" : "") + model.lp + " LP")
                              + "  ·  " + model.date
                    }
                }
            }
            Text {
                anchors.centerIn: parent
                visible: rows.count === 0
                text: "No games yet — play a Ranked Solo/Duo game"
                color: Theme.muted
                font.pixelSize: 12
            }
        }
}
