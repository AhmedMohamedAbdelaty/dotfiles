#!/usr/bin/env python3
"""Show and execute the recovered Lua keybindings using the existing Rofi theme."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
bindings = json.loads((root/'binds.json').read_text())
bindings.sort(key=lambda b: b['keybind'].upper())
if '-j' in sys.argv:
    for binding in bindings:
        print(json.dumps(binding))
    raise SystemExit(0)
labels = [b['keybind'] + '  →  ' + b['description'] for b in bindings]
if '-p' in sys.argv:
    print('\n'.join(labels))
    raise SystemExit(0)
selection = subprocess.run(['rofi', '-dmenu', '-i', '-no-custom', '-format', 'i',
                            '-p', 'Keybindings', '-theme', str(Path.home()/'.config/rofi/clipboard.rasi')],
                           input='\n'.join(labels), text=True, capture_output=True)
if selection.returncode:
    raise SystemExit(0)
binding = bindings[int(selection.stdout.strip())]
if not binding['mouse']:
    subprocess.run(['hyprctl', 'eval', 'hl.dispatch(' + binding['handler'] + ')'], check=True)
