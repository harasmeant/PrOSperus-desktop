# SPDX-License-Identifier: GPL-3.0-only
"""Fondos por horas: cada proyecto puede cambiar de imagen y de tono a lo largo del día, fundiendo
suavemente de una a otra. Se guarda en «.fondo.json» dentro de la carpeta que tiene el fondo:

    {"tono": "fondo", "fundido": 30,
     "horas": [{"hora": 7, "imagen": "wallpaper-07.jpg", "tono": "amanecer"},
               {"hora": 19, "imagen": null, "tono": "atardecer"}]}

«imagen» es un archivo de esa carpeta; null es el fondo de siempre (wallpaper.*)."""
import json
import os
from pathlib import Path

CONFIG = '.fondo.json'
DEFAULT_FADE = 30
MAX_FADE = 120


def load(folder):
    """Configuración de la carpeta, siempre completa y válida (vacía si no hay o está rota)."""
    try:
        data = json.loads((Path(folder) / CONFIG).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    hours, seen = [], set()
    for entry in data.get('horas', []) if isinstance(data.get('horas'), list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get('hora'), int) or not 0 <= entry['hora'] <= 23:
            continue
        if entry['hora'] in seen:
            continue
        image = entry.get('imagen')
        # Solo un nombre de archivo de la propia carpeta: nada de rutas ni carpetas ocultas.
        if image is not None and (not isinstance(image, str) or Path(image).name != image or image.startswith('.')):
            continue
        seen.add(entry['hora'])
        hours.append({'hora': entry['hora'], 'imagen': image, 'tono': str(entry.get('tono') or 'fondo')})
    fade = data.get('fundido', DEFAULT_FADE)
    fade = max(0, min(MAX_FADE, fade)) if isinstance(fade, int) else DEFAULT_FADE
    return {'tono': str(data.get('tono') or 'fondo'), 'fundido': fade, 'horas': sorted(hours, key=lambda e: e['hora'])}


def save(folder, data):
    path = Path(folder) / CONFIG
    temporary = path.with_name(CONFIG + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


# Borrador de qwen2.5-coder; reescrito (comparaba horas con minutos y no daba la vuelta a medianoche).
def blend(hours, minute, fade):
    """(anterior, actual, mezcla) para el minuto del día: la actual es la última hora ya empezada (antes de la
    primera, la última de ayer); la mezcla sube de 0 a 1 durante los primeros `fade` minutos."""
    current = len(hours) - 1
    for index, hour in enumerate(hours):
        if hour * 60 <= minute:
            current = index
    previous = (current - 1) % len(hours)
    if len(hours) == 1:
        return current, current, 1.0
    if fade <= 0:
        return previous, current, 1.0
    elapsed = (minute - hours[current] * 60) % 1440
    return previous, current, min(1.0, elapsed / fade)


def scene(folder, base, minute):
    """Qué se ve ahora: (imagen anterior, tono anterior, imagen actual, tono actual, mezcla).
    Las imágenes son rutas sin recolorear; sin horario, la anterior y la actual son la misma."""
    data = load(folder)
    if not data['horas']:
        return base, data['tono'], base, data['tono'], 1.0
    def image(entry):
        if entry['imagen']:
            candidate = Path(folder) / entry['imagen']
            if candidate.is_file() and not candidate.is_symlink():
                return candidate
        return base
    previous, current, mix = blend([e['hora'] for e in data['horas']], minute, data['fundido'])
    before, now = data['horas'][previous], data['horas'][current]
    return image(before), before['tono'], image(now), now['tono'], mix


def next_change(folder, minute):
    """Minutos hasta el siguiente cambio de hora (None sin horario): el escritorio solo despierta entonces."""
    hours = [e['hora'] * 60 for e in load(folder)['horas']]
    if not hours:
        return None
    return min((h - minute) % 1440 or 1440 for h in hours)
