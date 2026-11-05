import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Common

PanelWindow {
    id: root
    property Item target: null
    property var targetScreen: null
    property string detail: ""
    property bool vertical: false
    property bool shown: false
    property real targetX: 0
    property real targetY: 0

    function schedule() {
        if (detail && target && targetScreen) delay.restart()
    }
    function hide() {
        delay.stop()
        shown = false
    }
    function show() {
        if (!target || !targetScreen || !detail) return
        const position = target.mapToGlobal(0, 0)
        const x = position.x - (targetScreen.x || 0)
        const y = position.y - (targetScreen.y || 0)
        if (vertical) {
            targetX = x < targetScreen.width / 2 ? x + target.width + 8 : x - implicitWidth - 8
            targetY = y + target.height / 2 - implicitHeight / 2
        } else {
            targetX = x + target.width / 2 - implicitWidth / 2
            targetY = y < targetScreen.height / 2 ? y + target.height + 8 : y - implicitHeight - 8
        }
        shown = true
    }
    onDetailChanged: if (!detail) hide()

    Timer {
        id: delay
        interval: 500
        onTriggered: root.show()
    }

    screen: targetScreen
    WlrLayershell.namespace: "dms:tooltip"
    WlrLayershell.layer: WlrLayershell.Overlay
    WlrLayershell.exclusiveZone: -1
    anchors.top: true
    anchors.left: true
    margins.left: Math.round(Math.max(8, Math.min((targetScreen ? targetScreen.width : 800) - implicitWidth - 8, targetX)))
    margins.top: Math.round(Math.max(8, Math.min((targetScreen ? targetScreen.height : 600) - implicitHeight - 8, targetY)))
    implicitWidth: Math.min(480, Math.max(150, message.implicitWidth + 24))
    implicitHeight: Math.min(message.implicitHeight + 24, (targetScreen ? targetScreen.height : 600) - 16)
    color: "transparent"
    mask: Region {}
    visible: shown

    Rectangle {
        anchors.fill: parent
        color: Theme.tooltipSurface
        radius: Theme.cornerRadiusXS
        clip: true
        Text {
            id: message
            x: 12
            y: 12
            width: parent.width - 24
            text: root.detail
            textFormat: Text.PlainText
            color: Theme.tooltipText
            font.pixelSize: Theme.fontSizeSmall
            wrapMode: Text.Wrap
        }
    }
}
