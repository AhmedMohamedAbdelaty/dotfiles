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
    data.setdefault("intervals", {})
    data["intervals"].setdefault("system", 5)
    data["intervals"].setdefault("quick", 5)
    data["intervals"].setdefault("tools", 30)
    return data


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
    current_cpu = read_proc_stat()
    cpu = cpu_percent(previous.get("cpu_sample"), current_cpu)
    memory = memory_status()
    disk = disk_status()
    battery = battery_status()
    network = network_status()
    critical = cpu and cpu >= 90 or memory["percent"] >= 90 or disk["percent"] >= 95
    warning = cpu and cpu >= 75 or memory["percent"] >= 80 or disk["percent"] >= 90
    css = "system-critical" if critical else "system-warning" if warning else "system-good"
    text = f"󰍛 {cpu if cpu is not None else 0}%  󰘚 {memory['percent']}%"
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
    volume = volume_status()
    mic = mic_status()
    brightness = brightness_status()
    dnd = dnd_status()
    volume_label = "n/a" if volume["volume"] is None else f"{volume['volume']}%"
    brightness_label = "" if brightness["percent"] is None else f"  ☀ {brightness['percent']}%"
    muted = volume["muted"] or mic["muted"]
    css = "quick-muted" if muted else "quick-normal"
    if dnd["enabled"]:
        css = "quick-critical"
    text = f" {volume_label}{brightness_label}"
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


def collect_tools():
    session = session_summary()
    sync = sync_summary()
    if not sync["ok"]:
        css = "tools-error"
    elif session["count"] == 0:
        css = "tools-warning"
    else:
        css = "tools-good"
    text = f"🧰 {session['count']}"
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


def panel(name):
    if name == "system":
        section = collect_system(cache().get("system", {}))
        show_text_panel("System Health", section["tooltip"])
        return
    if name == "tools":
        body = collect_tools()["tooltip"]
        show_text_panel("Material Tools", body)
        return
    if name == "quick":
        body = collect_quick()["tooltip"] + "\n\nOpen dedicated apps for detailed control."
        show_text_panel("Quick Settings", body)
        return
    show_text_panel("Material Waybar", f"Unknown panel: {name}")


def show_settings():
    cfg = json.dumps(settings(), indent=2)
    show_text_panel("Material Waybar Settings", f"Settings file:\n{SETTINGS_FILE}\n\n{cfg}")


def refresh():
    data = {
        "system": collect_system(cache().get("system", {})),
        "quick": collect_quick(),
        "tools": collect_tools(),
    }
    save_cache(data)
    print(str(CACHE_FILE))


def usage():
    print("Usage: waybar-hub.py status <system|quick|tools> | panel <system|quick|tools> | settings | refresh")


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
