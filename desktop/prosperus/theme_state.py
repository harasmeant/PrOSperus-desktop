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
            f'[csd]\ncolor=cc{colors.panel[1:]}\nbutton-color=ff{colors.text[1:]}\n'
            f'button-minimize-color=ff{colors.card[1:]}\nbutton-maximize-color=ff{colors.card[1:]}\n'
            # Borde en el color de resalte del fondo, como las demás ventanas.
            f'border-width=2\nborder-color=ff{colors.accent[1:]}\n')


def fuzzel_config(colors):
    """Selector de fuzzel (historial del portapapeles) en los colores del proyecto."""
    c = lambda value, alpha='ff': value.lstrip('#') + alpha
    return (f"[main]\nfont=DejaVu Sans:size=12\nprompt='❯ '\nwidth=60\nlines=12\nhorizontal-pad=18\n"
            f"vertical-pad=14\ninner-pad=8\n\n[colors]\nbackground={c(colors.base, 'ee')}\n"
            f"text={c(colors.text)}\nprompt={c(colors.accent)}\ninput={c(colors.text)}\n"
            f"match={c(colors.accent)}\nselection={c(colors.card)}\nselection-text={c(colors.text)}\n"
            f"selection-match={c(colors.accent)}\nborder={c(colors.accent)}\n\n[border]\nwidth=2\nradius=14\n")


def wob_config(colors):
    """Barra de volumen y brillo (wob) en los colores del proyecto; «muted» la apaga."""
    c = lambda value, alpha='ff': value.lstrip('#') + alpha
    return ('timeout = 1200\nmax = 100\nwidth = 360\nheight = 34\nborder_offset = 0\nborder_size = 2\n'
            'bar_padding = 6\nanchor = bottom\nmargin = 140\noutput_mode = focused\n'
            f'background_color = {c(colors.base, "dd")}\nborder_color = {c(colors.accent)}\n'
            f'bar_color = {c(colors.text)}\n\n[style.muted]\nbar_color = {c(colors.muted)}\n')


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


def frame_traits(traits):
    """Rasgos de las ramas que se pueden compartir (números y gradiente; sin imágenes propias)."""
    shared = {k: float(v) for k, v in (traits or {}).items()
              if isinstance(v, (int, float)) and not isinstance(v, bool)}
    gradient = (traits or {}).get('branch_gradient')
    if isinstance(gradient, dict):
        shared['branch_gradient'] = {k: float(v) for k, v in gradient.items() if isinstance(v, (int, float))}
    return shared


def publish(colors, folder, directory=None, traits=None, wallpaper=None):
    """Guarda paleta (y rasgos de las ramas para las filigranas), carpeta, foot.ini y mako.conf;
    recarga mako si cambió. Nunca falla."""
    directory = directory or state_dir()
    if directory is None:
        return
    try:
        directory.mkdir(parents=True, exist_ok=True)
        data = {r: getattr(colors, r) for r in ROLES}
        data['traits'] = frame_traits(traits)
        # Fondo del proyecto: la pantalla de bloqueo lo muestra desenfocado (lock_screen.py).
        data['wallpaper'] = str(wallpaper) if wallpaper else ''
        _write(directory / 'theme.json', json.dumps(data))
        _write(directory / 'folder', str(folder) + '\n')
        _write(directory / 'foot.ini', foot_config(colors))
        _write(directory / 'fuzzel.ini', fuzzel_config(colors))
        # wob solo lee su configuración al arrancar: se cierra y la sesión lo vuelve a abrir.
        if _write(directory / 'wob.ini', wob_config(colors)):
            subprocess.run(['pkill', '-x', 'wob'], capture_output=True, timeout=3, check=False)
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


def current_traits(directory=None):
    """Rasgos de las ramas publicados por el escritorio (estilo de las filigranas); None si no hay."""
    directory = directory or state_dir()
    try:
        data = json.loads((directory / 'theme.json').read_text(encoding='utf-8'))
    except (OSError, TypeError, ValueError):
        return None
    traits = data.get('traits') if isinstance(data, dict) else None
    return frame_traits(traits) if isinstance(traits, dict) else None
