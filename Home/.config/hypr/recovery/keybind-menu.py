#!/usr/bin/env python3
"""Adapt recovered Lua bindings to the original HyDE menu's data and actions."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parent
bindings = json.loads((root/'binds.json').read_text())
if sys.argv[1:2] == ['--legacy-json']:
    masks = {'SHIFT': 1, 'CAPS': 2, 'CTRL': 4, 'CONTROL': 4, 'ALT': 8, 'SUPER': 64}
    rows = []
    for binding in bindings:
        parts = re.split(r'\s*\+\s*', binding['keybind'])
        options = binding['options']
        rows.append({
            'key': parts[-1], 'keycode': 0,
            'modmask': sum(masks[part.upper()] for part in parts[:-1]),
            'dispatcher': binding['dispatcher'], 'arg': binding['arg'],
            'description': binding['description'],
            'has_description': binding['has_description'],
            'locked': options.get('locked', False),
            'mouse': binding['mouse'], 'release': False,
            'repeat': options.get('repeating', False), 'non_consuming': False,
        })
    print(json.dumps(rows))
elif sys.argv[1:2] == ['--dispatch']:
    dispatcher, arg = sys.argv[2:4]
    for binding in bindings:
        if binding['dispatcher'] == dispatcher and binding['arg'].split() == arg.split():
            if not binding['mouse']:
                result = subprocess.run(['hyprctl', 'eval', 'hl.dispatch(' + binding['handler'] + ')'],
                                        capture_output=True, text=True)
                if result.returncode or result.stdout.strip() != 'ok':
                    sys.exit(result.stderr or result.stdout or 'Shortcut action failed')
            break
    else:
        sys.exit('Selected shortcut is no longer configured; reopen the menu.')
else:
    script = Path.home()/'.local/share/bin/keybinds_hint.sh'
    os.execv(str(script), [str(script), *sys.argv[1:]])
