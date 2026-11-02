#!/usr/bin/env python3
"""Rebuild Ahmed's native Lua config from the preserved HyDE config files."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path.home() / '.config/hypr'
variables = dict(os.environ)
output = ['-- Restored from the preserved HyDE .conf source chain.',
          '-- Rebuild after editing those files: python ~/.config/hypr/recovery/rebuild.py',
          'local startup, reload = {}, {}',
          '-- HyMission checks its Hyprland ABI before loading; failure must not break the desktop.',
          'pcall(hl.plugin.load, os.getenv("HOME") .. "/.local/lib/hymission.so")']
sources = []
bind_positions = {}
bindings = {}


def lua(value):
    if isinstance(value, dict):
        return '{ ' + ', '.join('[' + lua(k) + '] = ' + lua(v) for k, v in value.items()) + ' }'
    if isinstance(value, list):
        return '{ ' + ', '.join(map(lua, value)) + ' }'
    return json.dumps(value, ensure_ascii=False)


def expand(value):
    return re.sub(r'\$([A-Za-z_][A-Za-z_0-9]*)', lambda m: variables.get(m[1], m[0]), value)


def scalar(value):
    if value.lower() in ('true', 'yes', 'on'):
        return True
    if value.lower() in ('false', 'no', 'off'):
        return False
    if re.fullmatch(r'-?\d+', value):
        return int(value)
    if re.fullmatch(r'-?\d*\.\d+', value):
        return float(value)
    if 'deg' in value and ('rgba(' in value or 'rgb(' in value):
        return {'colors': re.findall(r'rgba?\([^)]*\)', value),
                'angle': int(re.search(r'(-?\d+)deg', value)[1])}
    return value


def config(path, value):
    if path == ['decoration', 'shadow', 'ignore_window'] and scalar(value) is True:
        # Removed in 0.55; shadows now always ignore the window itself.
        return
    value = scalar(value)
    for part in reversed(path):
        value = {part: value}
    output.append('hl.config(' + lua(value) + ')')


def rule(kind, text):
    effect, rest = text.split(',', 1)
    key, _, value = effect.strip().partition(' ')
    if kind == 'layer_rule' and 'match:' not in rest:
        # HyDE theme templates still use the pre-0.53 layer syntax.
        if key == 'unset':
            key, value = 'blur', 'false'
        elif not value:
            value = 'true'
        output.append('hl.layer_rule(' + lua({'match': {'namespace': rest.strip()}, key: scalar(value)}) + ')')
        return
    matches = {m[1]: m[2].strip().rstrip(',').strip() for m in re.finditer(
        r'match:(\w+)\s+(.+?)(?=,?\s+match:|$)', rest.strip())}
    if not matches:
        raise ValueError('Rule has no match: ' + text)
    output.append('hl.' + kind + '(' + lua({'match': matches, key: scalar(value)}) + ')')


def bind(kind, text, comment=''):
    parts = [p.strip() for p in text.split(',', 4 if 'd' in kind[4:] else 3)]
    mods, key = parts[:2]
    options = {}
    if 'd' in kind[4:]:
        options['description'] = parts.pop(2)
    action = parts[2]
    arg = parts[3] if len(parts) > 3 else ''
    if action == 'exec' and arg.startswith('dunstctl '):
        return
    mods = mods.replace('$CONTROL', 'CTRL')
    keys = ' + '.join(re.split(r'[+\s]+', mods.strip()) + [key]) if mods else key
    keys = keys.lstrip(' +')
    for flag, name in [('e', 'repeating'), ('l', 'locked'), ('m', 'mouse')]:
        if flag in kind[4:]:
            options[name] = True
    if action == 'exec':
        if 'hyprctl dispatch moveactive' in arg:
            dx, dy = map(int, re.search(r'moveactive\s+(-?\d+)\s+(-?\d+)', arg).groups())
            direction = 'left' if dx < 0 else 'right' if dx > 0 else 'up' if dy < 0 else 'down'
            handler = ('function() local w = hl.get_active_window(); if not w then return end; '
                       'if w.floating then hl.dispatch(hl.dsp.window.move({ x = %d, y = %d, relative = true })) '
                       'else hl.dispatch(hl.dsp.window.move({ direction = %s })) end end') % (dx, dy, lua(direction))
        else:
            handler = 'hl.dsp.exec_cmd(' + lua(arg) + ')'
    elif action == 'hymission:toggle':
        handler = ('function() pcall(function() hl.plugin.hymission.toggle('
                   + (lua(arg) if arg else '') + ') end) end')
    elif action == 'exit': handler = 'hl.dsp.exit()'
    elif action == 'togglefloating': handler = 'hl.dsp.window.float({ action = "toggle" })'
    elif action == 'togglegroup': handler = 'hl.dsp.group.toggle()'
    elif action == 'fullscreen': handler = 'hl.dsp.window.fullscreen()'
    elif action == 'changegroupactive': handler = 'hl.dsp.group.' + ('prev' if arg == 'b' else 'next') + '()'
    elif action == 'movefocus': handler = 'hl.dsp.focus({ direction = ' + lua({'l':'left','r':'right','u':'up','d':'down'}[arg]) + ' })'
    elif action == 'workspace': handler = 'hl.dsp.focus({ workspace = ' + lua(scalar(arg)) + ' })'
    elif action in ('movetoworkspace', 'movetoworkspacesilent'):
        handler = 'hl.dsp.window.move(' + lua({'workspace': scalar(arg), 'follow': action != 'movetoworkspacesilent'}) + ')'
    elif action == 'resizeactive':
        x, y = map(int, arg.split())
        handler = 'hl.dsp.window.resize(' + lua({'x':x,'y':y,'relative':True}) + ')'
    elif action == 'movewindow' and options.get('mouse'): handler = 'hl.dsp.window.drag()'
    elif action == 'resizewindow' and options.get('mouse'): handler = 'hl.dsp.window.resize()'
    elif action == 'togglespecialworkspace': handler = 'hl.dsp.workspace.toggle_special(' + lua(arg) + ')'
    else: raise ValueError('Unsupported bind: ' + text)
    statement = 'hl.bind(' + lua(keys) + ', ' + handler + (', ' + lua(options) if options else '') + ')'
    identity = keys.upper().replace(' ', '')
    description = options.get('description') or (comment[:1].upper() + comment[1:])
    bindings[identity] = {'keybind': keys, 'description': description or (action + ' ' + arg).strip(),
                          'handler': handler, 'mouse': options.get('mouse', False),
                          'dispatcher': action, 'arg': arg, 'options': options,
                          'has_description': bool(description)}
    if identity in bind_positions:
        output[bind_positions[identity]] = statement
    else:
        bind_positions[identity] = len(output)
        output.append(statement)


def read(path):
    path = Path(path).expanduser().resolve()
    if path in sources:
        raise ValueError('Duplicate or recursive source: ' + str(path))
    sources.append(path)
    output.append('\n-- ' + str(path.relative_to(ROOT)))
    stack = []
    special = None
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if not line: continue
        if line.endswith('{'):
            block = line[:-1].strip()
            if block in ('device', 'windowrule'):
                special = (block, {})
            else: stack.append(block)
            continue
        if line == '}':
            if special:
                block, spec = special
                output.append('hl.' + ('device' if block == 'device' else 'window_rule') + '(' + lua(spec) + ')')
                special = None
            else: stack.pop()
            continue
        key, value = map(str.strip, line.split('=', 1))
        value = expand(value)
        if key.startswith('$'):
            variables[key[1:]] = value
            continue
        if special:
            target = special[1]
            if key.startswith('match:'):
                target = target.setdefault('match', {})
                key = key[6:]
            target[key] = scalar(value)
        elif key == 'source': read(value)
        elif key == 'monitor':
            a = [p.strip() for p in value.split(',')]
            output.append('hl.monitor(' + lua(dict(zip(('output','mode','position','scale'), a))) + ')')
        elif key == 'env':
            name, val = value.split(',', 1)
            if name == 'PATH':
                output.append('do local path = os.getenv("PATH") or "/usr/local/bin:/usr/bin"; '
                              'local scripts = ' + lua(str(Path.home()/'.local/share/bin')) + '; '
                              'if not (":" .. path .. ":"):find(":" .. scripts .. ":", 1, true) then '
                              'path = path .. ":" .. scripts end; hl.env("PATH", path) end')
                continue
            output.append('hl.env(' + lua(name) + ', ' + lua(val) + ')')
        elif key == 'exec-once':
            # The final shortcut section and the existing session use swaync.
            if value == 'dunst': value = 'swaync'
            output.append('startup[#startup + 1] = ' + lua(value))
        elif key == 'exec': output.append('reload[#reload + 1] = ' + lua(value))
        elif key.startswith('bind'): bind(key, value, raw.partition('#')[2].strip())
        elif key == 'windowrule': rule('window_rule', value)
        elif key == 'layerrule': rule('layer_rule', value)
        elif key == 'blurls': rule('layer_rule', 'blur,' + value)
        elif key == 'bezier':
            name, x1, y1, x2, y2 = [p.strip() for p in value.split(',')]
            output.append('hl.curve(' + lua(name) + ', ' + lua({'type':'bezier','points':[[float(x1),float(y1)],[float(x2),float(y2)]]}) + ')')
        elif key == 'animation':
            a = [p.strip() for p in value.split(',')]
            spec = {'leaf':a[0], 'enabled':bool(int(a[1]))}
            if len(a) >= 4:
                spec.update(speed=float(a[2]), bezier=a[3])
            elif len(a) != 2 or spec['enabled']:
                raise ValueError('Invalid animation: ' + value)
            if len(a) > 4: spec['style'] = a[4]
            output.append('hl.animation(' + lua(spec) + ')')
        else: config(stack + re.split(r'[:.]', key), value)
    if stack or special: raise ValueError('Unclosed block: ' + str(path))


def main():
    read(ROOT/'hyprland.conf')
    output.append('''
local function refresh()
    if not hl.get_active_monitor() then return end
    -- Start search on demand so its helper does not delay overview input.
    pcall(function() hl.config({ plugin = { hymission = { vim_keys = true } } }) end)
    for _, command in ipairs(reload) do hl.exec_cmd(command) end
end
hl.on("config.reloaded", refresh)
hl.on("hyprland.start", function()
    refresh()
    for _, command in ipairs(startup) do hl.exec_cmd(command) end
end)
''')
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'hyprland.lua'
    with tempfile.NamedTemporaryFile(mode='w', prefix='.' + dest.stem + '-', suffix='.lua', dir=dest.parent, delete=False) as handle:
        handle.write('\n'.join(output).rstrip() + '\n')
        stage = Path(handle.name)
    try:
        with tempfile.TemporaryDirectory(prefix='hypr-verify-') as runtime:
            env = dict(os.environ, XDG_RUNTIME_DIR=runtime)
            env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
            check = subprocess.run(['Hyprland','--verify-config','-c',str(stage)], env=env, capture_output=True, text=True)
        if check.returncode:
            print(check.stdout + check.stderr, file=sys.stderr)
            raise SystemExit(check.returncode)
        stage.chmod(0o644)
        os.replace(stage, dest)
    finally:
        stage.unlink(missing_ok=True)
    if dest == ROOT/'hyprland.lua':
        menu = ROOT/'recovery/binds.json'
        menu.with_suffix('.pending.json').write_text(json.dumps(list(bindings.values()), indent=2) + '\n')
        os.replace(menu.with_suffix('.pending.json'), menu)
    print(f'Validated Lua config: {dest} ({len(sources)} source files)')


if __name__ == '__main__':
    main()
