# SPDX-License-Identifier: GPL-3.0-only
"""Tono del proyecto actual compartido con las demás ventanas de la sesión.

El escritorio publica en $XDG_RUNTIME_DIR/prosperus la paleta y la carpeta del proyecto
que se está viendo. Con eso:
- Foot (prosperus-terminal) abre en esa carpeta con su fondo y su barra en ese tono.
- Las notificaciones (mako) cambian de tono.
- Instalador y Fondos, que son programas aparte, usan la misma paleta.
Sin XDG_RUNTIME_DIR (pruebas, demo fuera de la sesión) no se escribe nada."""
import json
import os
import re
import subprocess
from pathlib import Path

from .appearance import Palette

ROLES = ('base', 'panel', 'card', 'hover', 'border', 'accent', 'text', 'muted', 'shade')
FOOT_BASE = '/etc/xdg/foot/foot.ini'
MAKO_BASE = '/etc/prosperus/mako.conf'


def state_dir():
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    return Path(runtime) / 'prosperus' if runtime else None


def foot_config(colors, base=FOOT_BASE):
    """foot.ini que parte del del sistema y solo cambia fondo, texto y barra de título."""
    return (f'[main]\ninclude={base}\n\n'
            f'[colors-dark]\nbackground={colors.base[1:]}\nforeground={colors.text[1:]}\n\n'
            f'[csd]\ncolor=99{colors.panel[1:]}\nbutton-color=ff{colors.text[1:]}\n'
            f'button-minimize-color=ff{colors.card[1:]}\nbutton-maximize-color=ff{colors.card[1:]}\n')


def mako_config(colors, base_text):
    """mako.conf del sistema con los colores del proyecto."""
    replace = {'background-color': colors.base + 'ee', 'text-color': colors.text,
               'border-color': colors.accent}
    for key, value in replace.items():
        base_text = re.sub(rf'(?m)^{key}=.*$', f'{key}={value}', base_text, count=1)
    return base_text


def _write(path, text):
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return False
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8'); tmp.replace(path)
    return True


def publish(colors, folder, directory=None):
    """Guarda paleta, carpeta, foot.ini y mako.conf; recarga mako si cambió. Nunca falla."""
    directory = directory or state_dir()
    if directory is None:
        return
    try:
        directory.mkdir(parents=True, exist_ok=True)
        _write(directory / 'theme.json', json.dumps({r: getattr(colors, r) for r in ROLES}))
        _write(directory / 'folder', str(folder) + '\n')
        _write(directory / 'foot.ini', foot_config(colors))
        base = Path(MAKO_BASE)
        if base.is_file() and _write(directory / 'mako.conf', mako_config(colors, base.read_text(encoding='utf-8'))):
            subprocess.run(['makoctl', 'reload'], capture_output=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def current_palette(directory=None):
    """Paleta publicada por el escritorio; la de siempre si no hay ninguna."""
    palette = Palette()
    directory = directory or state_dir()
    try:
        data = json.loads((directory / 'theme.json').read_text(encoding='utf-8'))
    except (OSError, TypeError, ValueError):
        return palette
    for role in ROLES:
        value = data.get(role)
        if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            setattr(palette, role, value)
    return palette
