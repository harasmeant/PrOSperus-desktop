# SPDX-License-Identifier: GPL-3.0-only
"""Carpetas ocultas del escritorio, guardadas por carpeta en `.prosperus-ocultos.json`.

Ocultar no toca los archivos: la carpeta sigue en el disco, en el explorador y en la
búsqueda; solo deja de dibujarse en el mapa. El archivo guarda nombres, no rutas, para
que la lista siga valiendo si el proyecto se mueve de sitio."""
import json
from pathlib import Path

FILE = '.prosperus-ocultos.json'


def hidden_names(folder):
    """Nombres ocultos en folder. Un archivo ausente o roto equivale a no ocultar nada."""
    try:
        data = json.loads((Path(folder) / FILE).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return set()
    names = data.get('ocultos') if isinstance(data, dict) else None
    if not isinstance(names, list):
        return set()
    return {name for name in names if isinstance(name, str) and name and '/' not in name}


def _save(folder, names):
    path = Path(folder) / FILE
    if not names:
        path.unlink(missing_ok=True); return
    temporary = path.with_name(FILE + '.tmp')
    temporary.write_text(json.dumps({'ocultos': sorted(names, key=str.lower)}, ensure_ascii=False, indent=2) + '\n',
                         encoding='utf-8')
    temporary.replace(path)


def _names(folder, paths):
    """Solo hijos directos de folder: no se oculta nada desde otra carpeta."""
    folder = Path(folder)
    return {Path(p).name for p in paths if Path(p).parent == folder}


def hide(folder, paths):
    _save(folder, hidden_names(folder) | _names(folder, paths))


def unhide(folder, paths):
    _save(folder, hidden_names(folder) - _names(folder, paths))


def is_hidden(path):
    path = Path(path)
    return path.name in hidden_names(path.parent)
