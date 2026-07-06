#!/usr/bin/env python3

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "material-settings.json"
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
CACHE_DIR = CACHE_HOME / "waybar"
CACHE_FILE = CACHE_DIR / "material-hub.json"

DEFAULT_SETTINGS = {
    "version": 1,
    "density": "balanced",
    "icon_mode": "emoji",
    "theme_mode": "wallbash",
    "modules": {
        "media": False,
        "hyprland": True,
        "system": True,
        "clock": True,
        "prayer": True,
        "workspaces": True,
        "taskbar": True,
        "quick": True,
        "tools": True,
        "timer": True,
        "notifications": True,
        "tray": True,
        "battery": True,
        "power": True,
    },
    "intervals": {
        "system": 5,
        "quick": 5,
        "tools": 30,
        "hyprland": 3,
    },
    "panels": {
        "backend": "yad",
        "confirm_power_actions": True,
    },
}

ICONS = {
    "emoji": {
        "cpu": "🧠",
        "memory": "💿",
        "volume": "🔊",
        "brightness": "☀",
        "tools": "🧰",
        "warning": "⚠",
        "settings": "⚙",
        "workspace": "🪟",
    },
    "nerd": {
        "cpu": "󰍛",
        "memory": "󰘚",
        "volume": "",
        "brightness": "󰃠",
        "tools": "󱂬",
        "warning": "󰀪",
        "settings": "",
        "workspace": "󰣇",
    },
    "plain": {
        "cpu": "CPU",
        "memory": "RAM",
        "volume": "VOL",
        "brightness": "BRI",
        "tools": "TOOLS",
        "warning": "!",
        "settings": "SET",
        "workspace": "WIN",
    },
}


def json_line(payload):
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def read_json(path, fallback=None):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return fallback


def write_json_atomic(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def settings():
    data = read_json(SETTINGS_FILE, {})
    if not isinstance(data, dict):
        data = {}
    data = merge_settings(DEFAULT_SETTINGS, data)
    data["density"] = data["density"] if data["density"] in {"compact", "balanced", "large"} else "balanced"
    data["icon_mode"] = data["icon_mode"] if data["icon_mode"] in ICONS else "emoji"
    for key, fallback in DEFAULT_SETTINGS["intervals"].items():
        try:
            data["intervals"][key] = max(1, int(data["intervals"].get(key, fallback)))
        except Exception:
            data["intervals"][key] = fallback
    return data


def merge_settings(defaults, current):
    merged = {}
    for key, value in defaults.items():
        if isinstance(value, dict):
            merged[key] = merge_settings(value, current.get(key, {}) if isinstance(current.get(key), dict) else {})
        else:
            merged[key] = current.get(key, value)
    for key, value in current.items():
        if key not in merged:
            merged[key] = value
    return merged


def save_settings(data):
    normalized = merge_settings(DEFAULT_SETTINGS, data)
    return write_json_atomic(SETTINGS_FILE, normalized)


def icon(name):
    cfg = settings()
    return ICONS[cfg["icon_mode"]].get(name, name)


def density():
    return settings().get("density", "balanced")


def cache():
    data = read_json(CACHE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_cache(data):
    data["updated_at"] = time.time()
    write_json_atomic(CACHE_FILE, data)


def run(args, timeout=0.7):
    try:
        result = subprocess.run(
            args,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip()
    except Exception:
        return 127, ""


def command_exists(name):
    return shutil.which(name) is not None


def read_proc_stat():
    try:
        fields = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
        values = [int(field) for field in fields]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        return {"total": total, "idle": idle}
    except Exception:
        return None


def cpu_percent(previous, current):
    if not current:
        return None
    if previous:
        total_delta = current["total"] - previous.get("total", 0)
        idle_delta = current["idle"] - previous.get("idle", 0)
        if total_delta > 0:
            return max(0, min(100, round((1 - idle_delta / total_delta) * 100)))
    try:
        load = os.getloadavg()[0]
        cores = max(1, os.cpu_count() or 1)
        return max(0, min(100, round((load / cores) * 100)))
    except Exception:
        return None


def memory_status():
    values = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0])
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", 0)
        used = max(0, total - available)
        percent = round((used / total) * 100) if total else 0
        return {
            "used_gb": round(used / 1024 / 1024, 1),
            "total_gb": round(total / 1024 / 1024, 1),
            "percent": percent,
        }
    except Exception:
        return {"used_gb": 0, "total_gb": 0, "percent": 0}


def disk_status():
    try:
        usage = shutil.disk_usage(Path.home())
        percent = round((usage.used / usage.total) * 100)
        return {
            "used_gb": round(usage.used / 1024 / 1024 / 1024, 1),
            "total_gb": round(usage.total / 1024 / 1024 / 1024, 1),
            "percent": percent,
        }
    except Exception:
        return {"used_gb": 0, "total_gb": 0, "percent": 0}


def battery_status():
    for path in Path("/sys/class/power_supply").glob("BAT*"):
        capacity = path / "capacity"
        status = path / "status"
        if capacity.exists():
            try:
                return {
                    "capacity": int(capacity.read_text(encoding="utf-8").strip()),
                    "status": status.read_text(encoding="utf-8").strip() if status.exists() else "Unknown",
                }
            except Exception:
                pass
    return None


def network_status():
    sys_net = Path("/sys/class/net")
    active = []
    for item in sys_net.iterdir() if sys_net.exists() else []:
        if item.name == "lo":
            continue
        try:
            if (item / "operstate").read_text(encoding="utf-8").strip() == "up":
                active.append(item.name)
        except Exception:
            continue
    ssid = ""
    if command_exists("iwgetid"):
        _, ssid = run(["iwgetid", "-r"], timeout=0.3)
    if ssid:
        return {"label": ssid, "interfaces": active}
    return {"label": active[0] if active else "offline", "interfaces": active}


def volume_status():
    if not command_exists("wpctl"):
        return {"volume": None, "muted": False}
    _, output = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], timeout=0.35)
    match = re.search(r"Volume:\s+([0-9.]+)", output)
    muted = "[MUTED]" in output
    volume = round(float(match.group(1)) * 100) if match else None
    return {"volume": volume, "muted": muted}


def mic_status():
    if not command_exists("wpctl"):
        return {"muted": False}
    _, output = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"], timeout=0.35)
    return {"muted": "[MUTED]" in output}


def brightness_status():
    if not command_exists("brightnessctl"):
        return {"percent": None}
    _, output = run(["brightnessctl", "-m"], timeout=0.35)
    parts = output.split(",")
    if len(parts) >= 4:
        try:
            return {"percent": int(parts[3].rstrip("%"))}
        except Exception:
            return {"percent": None}
    return {"percent": None}


def dnd_status():
    if not command_exists("swaync-client"):
        return {"available": False, "enabled": False}
    code, output = run(["swaync-client", "-D"], timeout=0.35)
    enabled = output.lower() in {"true", "1", "yes", "dnd"}
    return {"available": code == 0, "enabled": enabled}


def collect_system(previous=None):
    previous = previous or {}
    view = density()
    icons = settings()["icon_mode"]
    current_cpu = read_proc_stat()
    cpu = cpu_percent(previous.get("cpu_sample"), current_cpu)
    memory = memory_status()
    disk = disk_status()
    battery = battery_status()
    network = network_status()
    critical = (cpu is not None and cpu >= 90) or memory["percent"] >= 90 or disk["percent"] >= 95
    warning = (cpu is not None and cpu >= 75) or memory["percent"] >= 80 or disk["percent"] >= 90
    css = "system-critical" if critical else "system-warning" if warning else "system-good"
    cpu_label = cpu if cpu is not None else 0
    if view == "compact":
        text = f"{icon('cpu')} {cpu_label}%"
    elif view == "large":
        if icons == "plain":
            text = f"CPU {cpu_label}%  RAM {memory['percent']}%"
        else:
            text = f"{icon('cpu')} CPU {cpu_label}%  {icon('memory')} RAM {memory['percent']}%"
    else:
        text = f"{icon('cpu')} {cpu_label}%  {icon('memory')} {memory['percent']}%"
    tooltip = (
        f"CPU: {cpu if cpu is not None else 0}%\n"
        f"RAM: {memory['used_gb']}GB/{memory['total_gb']}GB ({memory['percent']}%)\n"
        f"Disk: {disk['used_gb']}GB/{disk['total_gb']}GB ({disk['percent']}%)\n"
        f"Network: {network['label']}"
    )
    if battery:
        tooltip += f"\nBattery: {battery['capacity']}% ({battery['status']})"
    return {
        "timestamp": time.time(),
        "cpu_sample": current_cpu,
        "text": text,
        "tooltip": tooltip,
        "class": css,
    }


def collect_quick():
    view = density()
    icons = settings()["icon_mode"]
    volume = volume_status()
    mic = mic_status()
    brightness = brightness_status()
    dnd = dnd_status()
    volume_label = "n/a" if volume["volume"] is None else f"{volume['volume']}%"
    brightness_label = "" if brightness["percent"] is None else f"  {icon('brightness')} {brightness['percent']}%"
    muted = volume["muted"] or mic["muted"]
    css = "quick-muted" if muted else "quick-normal"
    if dnd["enabled"]:
        css = "quick-critical"
    if view == "compact":
        text = f"{icon('volume')} {volume_label}"
    elif view == "large":
        bright_text = "unknown" if brightness["percent"] is None else f"{brightness['percent']}%"
        if icons == "plain":
            text = f"Volume {volume_label}  Bright {bright_text}"
        else:
            text = f"{icon('volume')} Volume {volume_label}  {icon('brightness')} Bright {bright_text}"
    else:
        text = f"{icon('volume')} {volume_label}{brightness_label}"
    tooltip = (
        f"Volume: {volume_label}{' muted' if volume['muted'] else ''}\n"
        f"Mic: {'muted' if mic['muted'] else 'active'}\n"
        f"Brightness: {brightness['percent'] if brightness['percent'] is not None else 'unknown'}\n"
        f"Do Not Disturb: {'on' if dnd['enabled'] else 'off'}\n"
        "Left click: quick settings\nRight click: Material settings\nMiddle click: toggle DND"
    )
    return {"timestamp": time.time(), "text": text, "tooltip": tooltip, "class": css}


def session_summary():
    state_file = CACHE_HOME / "hyde" / "session-restore.json"
    state = read_json(state_file, {})
    apps = state.get("apps", []) if isinstance(state, dict) else []
    return {
        "count": len(apps),
        "saved_at": state.get("saved_at", "never") if isinstance(state, dict) else "never",
        "apps": [app.get("name", "App") for app in apps if isinstance(app, dict)],
    }


def sync_summary():
    config = read_json(CONFIG_HOME / "hypr" / "dotfiles-sync.json", {})
    repo = config.get("repo_path", "") if isinstance(config, dict) else ""
    expected = config.get("branch", "") if isinstance(config, dict) else ""
    branch = ""
    if repo and (Path(repo) / ".git").exists():
        _, branch = run(["git", "-C", repo, "branch", "--show-current"], timeout=0.7)
    ok = bool(repo and branch and (not expected or branch == expected))
    return {"repo": repo, "expected_branch": expected, "branch": branch, "ok": ok}


def hypr_json(command, timeout=0.7):
    if not command_exists("hyprctl"):
        return None
    code, output = run(["hyprctl", "-j", command], timeout=timeout)
    if code != 0 or not output:
        return None
    try:
        return json.loads(output)
    except Exception:
        return None


def collect_hyprland(_previous=None):
    view = density()
    clients = hypr_json("clients") or []
    workspaces = hypr_json("workspaces") or []
    active_workspace = hypr_json("activeworkspace") or {}
    active_window = hypr_json("activewindow") or {}
    clients = clients if isinstance(clients, list) else []
    workspaces = workspaces if isinstance(workspaces, list) else []
    active_ws_id = active_workspace.get("id")

    grouped = {}
    for client in clients:
        workspace = client.get("workspace", {}) if isinstance(client, dict) else {}
        ws_id = workspace.get("id")
        if ws_id is None:
            continue
        grouped.setdefault(ws_id, []).append(client)

    non_special_workspaces = [
        ws for ws in workspaces
        if isinstance(ws, dict) and isinstance(ws.get("id"), int) and ws.get("id", 0) > 0
    ]
    visible_workspace_count = len(non_special_workspaces) or len([key for key in grouped if isinstance(key, int) and key > 0])
    active_count = len(grouped.get(active_ws_id, [])) if active_ws_id is not None else 0
    total_windows = len(clients)
    active_title = visible_text(active_window.get("title")) or visible_text(active_window.get("class")) or "Desktop"
    active_class = visible_text(active_window.get("class"))
    active_short = shorten(active_title, 30 if view == "large" else 18)

    if view == "compact":
        text = f"{icon('workspace')} {active_ws_id or '-'}:{active_count}"
    elif view == "large":
        if settings()["icon_mode"] == "plain":
            text = f"Workspace {active_ws_id or '-'} · {active_short}"
        else:
            text = f"{icon('workspace')} Workspace {active_ws_id or '-'} · {active_short}"
    else:
        text = f"{icon('workspace')} {active_ws_id or '-'} · {active_short}"

    tooltip_lines = [
        f"Active workspace: {active_ws_id or 'unknown'}",
        f"Active app: {active_class or 'unknown'}",
        f"Active title: {active_title}",
        f"Windows on workspace: {active_count}",
        f"Total windows: {total_windows}",
        f"Open workspaces: {visible_workspace_count}",
        "",
        "Left click: workspace window panel",
        "Right click: active window details",
        "Middle click: toggle special workspace",
    ]
    css = "hyprland-empty" if total_windows == 0 else "hyprland-active"
    return {
        "timestamp": time.time(),
        "text": text,
        "tooltip": "\n".join(tooltip_lines),
        "class": css,
        "clients": summarize_clients(clients),
        "workspaces": summarize_workspaces(workspaces),
        "active_workspace": active_ws_id,
        "active_title": active_title,
    }


def shorten(text, limit):
    text = visible_text(text)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def visible_text(text):
    text = str(text or "")
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]", "", text)
    return " ".join(text.split())


def summarize_clients(clients):
    summary = []
    for client in clients:
        if not isinstance(client, dict):
            continue
        workspace = client.get("workspace", {}) if isinstance(client.get("workspace"), dict) else {}
        summary.append({
            "address": client.get("address", ""),
            "class": visible_text(client.get("class")),
            "title": visible_text(client.get("title")),
            "workspace": workspace.get("id"),
            "workspace_name": workspace.get("name", ""),
            "floating": bool(client.get("floating")),
            "fullscreen": client.get("fullscreen", 0),
        })
    summary.sort(key=lambda item: (item.get("workspace") or 9999, item.get("class") or "", item.get("title") or ""))
    return summary


def summarize_workspaces(workspaces):
    summary = []
    for workspace in workspaces:
        if not isinstance(workspace, dict):
            continue
        summary.append({
            "id": workspace.get("id"),
            "name": workspace.get("name", ""),
            "windows": workspace.get("windows", 0),
            "monitor": workspace.get("monitor", ""),
        })
    summary.sort(key=lambda item: item.get("id") if isinstance(item.get("id"), int) else 9999)
    return summary


def collect_tools():
    view = density()
    icons = settings()["icon_mode"]
    session = session_summary()
    sync = sync_summary()
    if not sync["ok"]:
        css = "tools-error"
    elif session["count"] == 0:
        css = "tools-warning"
    else:
        css = "tools-good"
    if view == "compact":
        text = f"{icon('tools')} {session['count']}"
    elif view == "large":
        if icons == "plain":
            text = f"Tools · Session {session['count']}"
        else:
            text = f"{icon('tools')} Tools · Session {session['count']}"
    else:
        text = f"{icon('tools')} {session['count']}"
    tooltip = (
        f"Session apps: {session['count']}\n"
        f"Saved: {session['saved_at']}\n"
        f"Apps: {', '.join(session['apps']) if session['apps'] else 'none'}\n\n"
        f"Dotfiles repo: {sync['repo'] or 'not configured'}\n"
        f"Branch: {sync['branch'] or 'unknown'}\n"
        f"Expected: {sync['expected_branch'] or 'any'}\n"
        "Left click: tools panel\nRight click: safe sync GUI\nMiddle click: save session"
    )
    return {"timestamp": time.time(), "text": text, "tooltip": tooltip, "class": css}


def cached_section(name, collector, ttl):
    data = cache()
    section = data.get(name, {})
    if not isinstance(section, dict) or time.time() - section.get("timestamp", 0) > ttl:
        section = collector(section)
        data[name] = section
        save_cache(data)
    return section


def status(name):
    cfg = settings()
    intervals = cfg.get("intervals", {})
    if name == "system":
        section = cached_section("system", collect_system, int(intervals.get("system", 5)))
    elif name == "quick":
        section = cached_section("quick", lambda _: collect_quick(), int(intervals.get("quick", 5)))
    elif name == "tools":
        section = cached_section("tools", lambda _: collect_tools(), int(intervals.get("tools", 30)))
    elif name == "hyprland":
        section = cached_section("hyprland", collect_hyprland, int(intervals.get("hyprland", 3)))
    else:
        json_line({"text": "?", "tooltip": f"Unknown status: {name}", "class": "tools-error"})
        return
    json_line({key: section[key] for key in ("text", "tooltip", "class") if key in section})


def show_text_panel(title, body):
    if command_exists("yad"):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, prefix="waybar-material-", suffix=".txt")
        with handle:
            handle.write(body)
        subprocess.Popen([
            "yad",
            "--text-info",
            f"--title={title}",
            "--width=760",
            "--height=520",
            f"--filename={handle.name}",
            "--button=Close:0",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif command_exists("notify-send"):
        subprocess.Popen(["notify-send", title, body[:400]])
    else:
        print(body)


def launch(args):
    if not args:
        return False
    if shutil.which(args[0]) is None and "/" not in args[0]:
        return False
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def shell_launch(command):
    try:
        subprocess.Popen(["bash", "-lc", command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def notify(title, body=""):
    if command_exists("notify-send"):
        launch(["notify-send", "-a", "Material Waybar", title, body])


def run_action(action):
    actions = {
        "volume-down": ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"],
        "volume-up": ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"],
        "volume-mute": ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
        "mic-toggle": ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"],
        "brightness-down": ["brightnessctl", "set", "5%-"],
        "brightness-up": ["brightnessctl", "set", "5%+"],
        "notifications": ["swaync-client", "-t", "-sw"],
        "dnd-toggle": ["swaync-client", "-d", "-sw"],
        "session-save": ["bash", str(Path.home() / ".local/share/bin/hypr-session.sh"), "save"],
        "session-restore": ["bash", str(Path.home() / ".local/share/bin/hypr-session.sh"), "restore"],
        "session-gui": ["bash", str(Path.home() / ".local/share/bin/hypr-session.sh"), "gui"],
        "sync-gui": ["bash", str(Path.home() / ".local/share/bin/dotfiles-sync.sh"), "gui"],
        "sync-preview": ["bash", str(Path.home() / ".local/share/bin/dotfiles-sync.sh"), "sync", "--dry-run"],
        "power": ["logoutlaunch.sh", "2"],
    }
    shell_actions = {
        "wallpaper-next": "swwwallpaper.sh -n",
        "wallpaper-select": "swwwallselect.sh",
        "theme-next": "themeswitch.sh -n",
        "theme-select": "themeselect.sh",
        "clipboard": "cliphist.sh c",
    }
    if action in actions:
        ok = launch(actions[action])
    elif action in shell_actions:
        ok = shell_launch(shell_actions[action])
    else:
        ok = False
    if ok:
        refresh()
    else:
        notify("Action unavailable", action)
    return ok


def yad_question(title, text, ok="Continue"):
    if not command_exists("yad"):
        return False
    result = subprocess.run(
        ["yad", "--question", f"--title={title}", f"--text={text}", "--button=Cancel:1", f"--button={ok}:0"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def hyprland_panel():
    section = collect_hyprland()
    clients = section.get("clients", [])
    if not clients:
        show_text_panel("Workspace Windows", "No windows are open.")
        return
    if not command_exists("yad"):
        body = "\n".join(
            f"Workspace {item.get('workspace')}: {item.get('class')} - {item.get('title')}"
            for item in clients
        )
        show_text_panel("Workspace Windows", body)
        return

    rows = []
    for item in clients:
        rows.extend([
            str(item.get("workspace") or ""),
            item.get("class") or "",
            shorten(item.get("title") or "", 80),
            item.get("address") or "",
        ])
    result = subprocess.run(
        [
            "yad",
            "--list",
            "--title=Workspace Windows",
            "--width=920",
            "--height=560",
            "--column=Workspace",
            "--column=Class",
            "--column=Title",
            "--column=Address",
            "--hide-column=4",
            "--print-column=4",
            "--button=Focus:10",
            "--button=Move Here:20",
            "--button=Toggle Float:30",
            "--button=Close:40",
            "--button=Refresh:50",
            "--button=Close Panel:0",
            *rows,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    address = result.stdout.strip().split("|")[-1] if result.stdout.strip() else ""
    if result.returncode == 50:
        refresh()
        hyprland_panel()
        return
    if not address:
        return
    if result.returncode == 10:
        run(["hyprctl", "dispatch", "focuswindow", f"address:{address}"], timeout=0.7)
    elif result.returncode == 20:
        run(["hyprctl", "dispatch", "movetoworkspace", "current", f"address:{address}"], timeout=0.7)
    elif result.returncode == 30:
        run(["hyprctl", "dispatch", "togglefloating", f"address:{address}"], timeout=0.7)
    elif result.returncode == 40:
        if yad_question("Close Window", "Close the selected window?", "Close"):
            run(["hyprctl", "dispatch", "closewindow", f"address:{address}"], timeout=0.7)
    refresh()


def quick_panel():
    quick = collect_quick()
    text = (
        f"{quick['tooltip']}\n\n"
        "Choose an action. Missing tools simply do nothing and notify you."
    )
    if not command_exists("yad"):
        show_text_panel("Quick Settings", text)
        return
    result = subprocess.run(
        [
            "yad",
            "--form",
            "--title=Material Quick Settings",
            "--width=520",
            f"--text={text}",
            "--button=Vol -:10",
            "--button=Vol +:11",
            "--button=Mute:12",
            "--button=Mic:13",
            "--button=Dim:20",
            "--button=Bright:21",
            "--button=DND:30",
            "--button=Notify:31",
            "--button=Wallpaper:40",
            "--button=Theme:41",
            "--button=Clipboard:42",
            "--button=Close:0",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    action_map = {
        10: "volume-down",
        11: "volume-up",
        12: "volume-mute",
        13: "mic-toggle",
        20: "brightness-down",
        21: "brightness-up",
        30: "dnd-toggle",
        31: "notifications",
        40: "wallpaper-select",
        41: "theme-select",
        42: "clipboard",
    }
    action = action_map.get(result.returncode)
    if action:
        run_action(action)


def tools_panel():
    tools = collect_tools()
    text = tools["tooltip"]
    if not command_exists("yad"):
        show_text_panel("Material Tools", text)
        return
    result = subprocess.run(
        [
            "yad",
            "--form",
            "--title=Material Tools",
            "--width=560",
            f"--text={text}",
            "--button=Save Session:10",
            "--button=Restore Session:11",
            "--button=Session GUI:12",
            "--button=Sync GUI:20",
            "--button=Preview Sync:21",
            "--button=Settings:30",
            "--button=Close:0",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    action_map = {
        10: "session-save",
        11: "session-restore",
        12: "session-gui",
        20: "sync-gui",
        21: "sync-preview",
    }
    if result.returncode == 30:
        show_settings()
        return
    action = action_map.get(result.returncode)
    if action:
        if action == "session-restore" and not yad_question("Restore Session", "Restore saved session apps now?", "Restore"):
            return
        run_action(action)


def panel(name):
    if name == "system":
        section = collect_system(cache().get("system", {}))
        show_text_panel("System Health", section["tooltip"])
        return
    if name == "tools":
        tools_panel()
        return
    if name == "quick":
        quick_panel()
        return
    if name == "hyprland":
        hyprland_panel()
        return
    show_text_panel("Material Waybar", f"Unknown panel: {name}")


def show_settings():
    cfg = settings()
    if not command_exists("yad"):
        show_text_panel("Material Waybar Settings", f"Settings file:\n{SETTINGS_FILE}\n\n{json.dumps(cfg, indent=2)}")
        return
    density_choices = "!".join([cfg["density"]] + [item for item in ["compact", "balanced", "large"] if item != cfg["density"]])
    icon_choices = "!".join([cfg["icon_mode"]] + [item for item in ["emoji", "nerd", "plain"] if item != cfg["icon_mode"]])
    result = subprocess.run(
        [
            "yad",
            "--form",
            "--title=Material Waybar Settings",
            "--width=520",
            f"--text=Settings file: {SETTINGS_FILE}",
            "--field=Density:CB",
            density_choices,
            "--field=Icon mode:CB",
            icon_choices,
            "--field=System interval seconds:NUM",
            f"{cfg['intervals']['system']}!1..60!1",
            "--field=Quick interval seconds:NUM",
            f"{cfg['intervals']['quick']}!1..60!1",
            "--field=Tools interval seconds:NUM",
            f"{cfg['intervals']['tools']}!5..300!5",
            "--field=Hyprland interval seconds:NUM",
            f"{cfg['intervals']['hyprland']}!1..60!1",
            "--button=Cancel:1",
            "--button=Save:0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return
    fields = result.stdout.rstrip("\n").split("|")
    if len(fields) < 6:
        notify("Settings not saved", "Unexpected settings form output.")
        return
    cfg["density"] = fields[0] if fields[0] in {"compact", "balanced", "large"} else "balanced"
    cfg["icon_mode"] = fields[1] if fields[1] in ICONS else "emoji"
    for key, raw in [("system", fields[2]), ("quick", fields[3]), ("tools", fields[4]), ("hyprland", fields[5])]:
        try:
            cfg["intervals"][key] = max(1, int(float(raw)))
        except Exception:
            pass
    if save_settings(cfg):
        refresh()
        notify("Material Waybar settings saved", f"Density: {cfg['density']}, icons: {cfg['icon_mode']}")
    else:
        notify("Settings not saved", str(SETTINGS_FILE))


def refresh():
    data = {
        "system": collect_system(cache().get("system", {})),
        "quick": collect_quick(),
        "tools": collect_tools(),
        "hyprland": collect_hyprland(),
    }
    save_cache(data)
    print(str(CACHE_FILE))


def usage():
    print("Usage: waybar-hub.py status <system|quick|tools|hyprland> | panel <system|quick|tools|hyprland> | settings | refresh")


def main(argv):
    if len(argv) < 2:
        usage()
        return 1
    command = argv[1]
    if command == "status" and len(argv) >= 3:
        status(argv[2])
        return 0
    if command == "panel" and len(argv) >= 3:
        panel(argv[2])
        return 0
    if command == "settings":
        show_settings()
        return 0
    if command == "refresh":
        refresh()
        return 0
    usage()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
