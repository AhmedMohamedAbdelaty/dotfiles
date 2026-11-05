import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: root
    property string pluginId: ""
    property var pluginService: null

    function clean(text) {
        return text.replace(/<[^>]*>/g, "").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&amp;/g, "&")
    }

    function publish(text, tooltip) {
        if (pluginService && pluginId)
            pluginService.setGlobalVar(pluginId, "status", {text: text, tooltip: tooltip})
    }

    Timer {
        interval: 300000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: if (!status.running) status.running = true
    }
    Process {
        id: status
        command: ["bash", Quickshell.env("HOME") + "/.local/share/bin/dotfiles-sync.sh", "waybar"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text)
                    if (typeof data.text !== "string" || (0 > 0 && (!data._duxUpdated || Date.now() / 1000 - data._duxUpdated > 0)))
                        throw new Error("invalid or stale status")
                    root.publish(root.clean(data.text), typeof data.tooltip === "string" ? root.clean(data.tooltip) : "")
                } catch (error) {
                    root.publish("Dotfiles unavailable", "")
                }
            }
        }
        onExited: (code, status) => {
            if (code !== 0) root.publish("Dotfiles unavailable", "")
        }
    }
}
