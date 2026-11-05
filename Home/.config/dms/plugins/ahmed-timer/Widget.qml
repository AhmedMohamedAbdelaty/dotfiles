import QtQuick
import "../../shared/ahmed" as Shared
import Quickshell
import qs.Common
import qs.Modules.Plugins

PluginComponent {
    id: root
    property string detail: ""
    property string label: "Timer unavailable"

    function refresh() {
        const status = pluginService && pluginId ? pluginService.getGlobalVar(pluginId, "status", null) : null
        label = status ? status.text : "Timer unavailable"
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
    pillClickAction: () => Quickshell.execDetached([Quickshell.env("HOME") + "/.config/waybar/timer-manager.py", "menu"])
    pillRightClickAction: () => Quickshell.execDetached([Quickshell.env("HOME") + "/.config/waybar/timer-manager.py", "toggle"])
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
