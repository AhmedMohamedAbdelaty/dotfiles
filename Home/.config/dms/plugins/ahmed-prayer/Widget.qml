import QtQuick
import "../../shared/ahmed" as Shared
import QtQuick.Controls
import Quickshell
import qs.Common
import qs.Modules.Plugins

PluginComponent {
    id: root
    property string detail: ""
    property string label: "Prayer times unavailable"

    function refresh() {
        const status = pluginService && pluginId ? pluginService.getGlobalVar(pluginId, "status", null) : null
        label = status ? status.text : "Prayer times unavailable"
        detail = status ? status.tooltip : ""
    }
    onPluginServiceChanged: refresh()
    onPluginIdChanged: refresh()
    Connections {
        target: root.pluginService
        function onGlobalVarChanged(changedPluginId, name) {
            if (changedPluginId === root.pluginId && name === "status") root.refresh()
        }
    }

    popoutWidth: 400
    popoutContent: Component {
        Item {
            implicitHeight: 340
            Text {
                id: heading
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                text: "Prayer times"
                color: Theme.surfaceText
                font.pixelSize: Theme.fontSizeLarge
                font.bold: true
            }
            Flickable {
                anchors.top: heading.bottom
                anchors.topMargin: 12
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                clip: true
                contentWidth: width
                contentHeight: details.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { }
                Text {
                    id: details
                    width: parent.width - 12
                    text: root.detail || "No details available."
                    textFormat: Text.PlainText
                    color: Theme.surfaceText
                    font.pixelSize: Theme.fontSizeMedium
                    wrapMode: Text.Wrap
                }
            }
        }
    }

    horizontalBarPill: Component {
        Text {
            id: pillText
            text: root.label
            textFormat: Text.PlainText
            font.pixelSize: root.textSize
            color: Theme.surfaceText
            HoverHandler {
                onHoveredChanged: hovered ? tooltip.schedule() : tooltip.hide()
            }
            Shared.StatusTooltip {
                id: tooltip
                target: pillText
                targetScreen: root.parentScreen
                detail: root.detail
                vertical: root.isVertical
            }
        }
    }
    verticalBarPill: Component {
        Text {
            id: pillText
            text: root.label
            textFormat: Text.PlainText
            font.pixelSize: root.textSize
            color: Theme.surfaceText
            HoverHandler {
                onHoveredChanged: hovered ? tooltip.schedule() : tooltip.hide()
            }
            Shared.StatusTooltip {
                id: tooltip
                target: pillText
                targetScreen: root.parentScreen
                detail: root.detail
                vertical: root.isVertical
            }
        }
    }
}
