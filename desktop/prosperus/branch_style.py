# SPDX-License-Identifier: GPL-3.0-only
"""Ajustes personales de las ramas del mapa, por carpeta y heredados por las subcarpetas.

Sin archivo, todo sale del fondo (modo automático). El archivo `.prosperus-ramas.json`
puede fijar el estilo (déco, nouveau, brotes) y retocar curvatura, grosor y opacidad."""
from functools import lru_cache
import json
from pathlib import Path
import shutil

FILE = '.prosperus-ramas.json'
# Rasgos del estilo: si faltan, se usan los del fondo.
STYLE_KEYS = ('straight', 'magic', 'detail')
# Retoques: multiplicadores, 1 = sin cambio.
TWEAKS = {'curl': (0.0, 2.5), 'width': (0.4, 2.5), 'opacity': (0.2, 1.6)}
# Adornos: piezas de serie o imágenes propias guardadas junto al archivo de ajustes.
IMAGES = '.prosperus-adornos'
BUILTIN = ('seta', 'lirio', 'pavo', 'zarcillo', 'hoja', 'greca', 'rombo', 'destello')
IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
PLACES = ('rama', 'brote')
MAX_ORNAMENTS = 12


def settings_file(folder, stop=None):
    """Archivo de ajustes de folder o del ancestro más cercano (hasta stop, incluido)."""
    current = Path(folder)
    stop = Path(stop) if stop else None
    while True:
        candidate = current / FILE
        if candidate.is_file():
            return candidate
        if current == stop or current.parent == current or current == Path.home():
            return None
        current = current.parent


@lru_cache(maxsize=32)
def _read(path, modified):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def clean(data, base=None):
    """Solo claves conocidas y valores dentro de rango. base: carpeta del archivo (para las imágenes)."""
    result = {}
    if not data.get('auto', True):
        for key in STYLE_KEYS:
            if isinstance(data.get(key), (int, float)):
                result[key] = max(0.0, min(1.0, float(data[key])))
    for key, (low, high) in TWEAKS.items():
        if isinstance(data.get(key), (int, float)):
            result[key] = max(low, min(high, float(data[key])))
    ornaments = []
    for item in data.get('ornaments', []) if isinstance(data.get('ornaments'), list) else []:
        if not isinstance(item, dict) or len(ornaments) >= MAX_ORNAMENTS:
            continue
        kind = item.get('kind')
        entry = {'kind': kind,
                 'every': max(1, min(20, int(item['every']))) if isinstance(item.get('every'), (int, float)) else 3,
                 'place': item.get('place') if item.get('place') in PLACES else 'rama',
                 'size': max(.3, min(3.0, float(item['size']))) if isinstance(item.get('size'), (int, float)) else 1.0,
                 'tint': item.get('tint') is not False}
        if kind == 'imagen':
            # Solo el nombre: la imagen tiene que estar en .prosperus-adornos de esa carpeta.
            name = Path(str(item.get('file', ''))).name
            if base is None or not name or Path(name).suffix.lower() not in IMAGE_SUFFIXES:
                continue
            path = Path(base) / IMAGES / name
            if not path.is_file():
                continue
            entry.update(file=name, path=path)
        elif kind not in BUILTIN:
            continue
        ornaments.append(entry)
    if ornaments:
        result['ornaments'] = ornaments
    return result


def add_image(folder, source):
    """Copia una imagen propia a la carpeta (viaja con ella) y devuelve el nombre con que guardarla."""
    source = Path(source)
    if source.suffix.lower() not in IMAGE_SUFFIXES or not source.is_file():
        raise ValueError('Elige una imagen PNG, JPG, WEBP o GIF.')
    target_dir = Path(folder) / IMAGES
    target_dir.mkdir(exist_ok=True)
    target, number = target_dir / source.name, 2
    while target.exists() and not target.samefile(source):
        target = target_dir / f'{source.stem}-{number}{source.suffix}'; number += 1
    if not target.exists():
        shutil.copyfile(source, target)
    return target.name


def load(folder, stop=None):
    """Ajustes efectivos ({} si no hay archivo): ya validados."""
    path = settings_file(folder, stop)
    if path is None:
        return {}
    try:
        return clean(_read(str(path), path.stat().st_mtime_ns), path.parent)
    except OSError:
        return {}


def raw(folder, stop=None):
    """Contenido del archivo tal cual (para mostrarlo en la aplicación)."""
    path = settings_file(folder, stop)
    if path is None:
        return {}
    try:
        return dict(_read(str(path), path.stat().st_mtime_ns))
    except OSError:
        return {}


def merge(traits, overrides):
    """Rasgos del fondo con los ajustes personales encima."""
    merged = dict(traits or {})
    merged.update(overrides)
    return merged


def save(folder, data):
    folder = Path(folder)
    if folder == Path.home() or folder == Path('/') or not folder.is_dir():
        raise ValueError('Elige una carpeta de proyecto.')
    target = folder / FILE
    temporary = folder / (FILE + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(target)
    return target


def reset(folder):
    """Vuelve al modo automático en esta carpeta (hereda de las de arriba si tienen ajustes)."""
    try:
        (Path(folder) / FILE).unlink()
    except FileNotFoundError:
        pass
