# SPDX-License-Identifier: GPL-3.0-only
"""Tono del proyecto actual compartido con las demás ventanas de la sesión.

El escritorio publica en $XDG_RUNTIME_DIR/prosperus la paleta y la carpeta del proyecto
que se está viendo. Con eso:
- kitty (prosperus-terminal) abre en esa carpeta con su fondo y su barra en ese tono.
- Las notificaciones (mako) cambian de tono.
- Instalador y Fondos, que son programas aparte, usan la misma paleta.
Sin XDG_RUNTIME_DIR (pruebas, demo fuera de la sesión) no se escribe nada."""
import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

from .appearance import Palette

ROLES = ('base', 'panel', 'card', 'hover', 'border', 'accent', 'text', 'muted', 'shade')
KITTY_BASE = '/etc/xdg/kitty/kitty.conf'
MAKO_BASE = '/etc/prosperus/mako.conf'


def state_dir():
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    return Path(runtime) / 'prosperus' if runtime else None


def kitty_config(colors, base=KITTY_BASE):
    """kitty.conf que parte del del sistema y solo cambia fondo y texto (la barra de título toma el fondo)."""
    return f'include {base}\nbackground {colors.base}\nforeground {colors.text}\nselection_background {colors.card}\n'


def fuzzel_config(colors):
    """Selector de fuzzel (historial del portapapeles) en los colores del proyecto."""
    c = lambda value, alpha='ff': value.lstrip('#') + alpha
    return (f"[main]\nfont=DejaVu Sans:size=12\nprompt='❯ '\nwidth=60\nlines=12\nhorizontal-pad=18\n"
            f"vertical-pad=14\ninner-pad=8\n\n[colors]\nbackground={c(colors.base)}\n"
            f"text={c(colors.text)}\nprompt={c(colors.accent)}\ninput={c(colors.text)}\n"
            f"match={c(colors.accent)}\nselection={c(colors.card)}\nselection-text={c(colors.text)}\n"
            f"selection-match={c(colors.accent)}\nborder={c(colors.accent)}\n\n[border]\nwidth=0\nradius=14\n")


@lru_cache(maxsize=None)
def program_version(program):
    """(mayor, menor) de un programa con --version; None si no se sabe (se supone el más reciente)."""
    try:
        version = subprocess.run([program, '--version'], capture_output=True, text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    found = re.search(r'(\d+)\.(\d+)', version)
    return (int(found[1]), int(found[2])) if found else None


def wob_version():
    return program_version('wob')


def wob_config(colors, version=None):
    """Barra de volumen y brillo (wob) en los colores del proyecto; «muted» la apaga.

    Cada versión rechaza el archivo entero si ve algo que no conoce: output_mode solo
    hasta 0.15 (Fedora; 0.16 en Arch lo quitó) y [style.muted] desde 0.15 (Debian trae 0.14)."""
    c = lambda value, alpha='ff': value.lstrip('#') + alpha
    if version is None:
        version = wob_version() or (0, 15)
    return ('timeout = 1200\nmax = 100\nwidth = 360\nheight = 34\nborder_offset = 0\nborder_size = 0\n'
            'bar_padding = 6\nanchor = bottom\nmargin = 140\n' + ('output_mode = focused\n' if version < (0, 16) else '') +
            f'background_color = {c(colors.base)}\nborder_color = {c(colors.accent)}\n'
            f'bar_color = {c(colors.text)}\n' +
            (f'\n[style.muted]\nbar_color = {c(colors.muted)}\n' if version >= (0, 15) else ''))


def swappy_config(colors, captures):
    """Editor de capturas (swappy): guarda en la carpeta de capturas y dibuja con el resalte del proyecto."""
    red, green, blue = (int(colors.accent[i:i + 2], 16) for i in (1, 3, 5))
    return (f'[Default]\nsave_dir={captures}\nsave_filename_format=Captura %Y-%m-%d %H.%M.%S.png\n'
            'show_panel=true\nline_size=5\ntext_size=20\ntext_font=DejaVu Sans\npaint_mode=arrow\n'
            f'early_exit=false\nfill_shape=false\ncustom_color=rgba({red},{green},{blue},1)\n')


def mako_config(colors, base_text):
    """mako.conf del sistema con los colores del proyecto."""
    replace = {'background-color': colors.base + 'ff', 'text-color': colors.text,
               'border-color': colors.accent}
    for key, value in replace.items():
        base_text = re.sub(rf'(?m)^{key}=.*$', f'{key}={value}', base_text, count=1)
    return base_text


# Evitar sobrescribir archivos idénticos
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


def _pictures():
    """Carpeta de imágenes del usuario (xdg-user-dir), Imágenes si no se sabe."""
    try:
        out = subprocess.run(['xdg-user-dir', 'PICTURES'], capture_output=True, text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ''
    home = str(Path.home())
    return out if out and out != home else home + '/Imágenes'


def publish(colors, folder, directory=None, traits=None, wallpaper=None, project=None):
    """Guarda paleta (y rasgos de las ramas para las filigranas), carpeta, kitty.conf y mako.conf;
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
        _write(directory / 'kitty.conf', kitty_config(colors))
        _write(directory / 'fuzzel.ini', fuzzel_config(colors))
        swappy = directory / 'xdg' / 'swappy'
        swappy.mkdir(parents=True, exist_ok=True)
        # Capturas en <proyecto>/Capturas (fuera de un proyecto, Imágenes/Capturas).
        captures = Path(project) / 'Capturas' if project else Path(_pictures()) / 'Capturas'
        _write(directory / 'capturas', str(captures) + '\n')
        _write(swappy / 'config', swappy_config(colors, captures))
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
