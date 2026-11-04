# SPDX-License-Identifier: GPL-3.0-only
"""Tonos del escritorio: la misma imagen de fondo con otros colores, sin perder su diseño.

Tres grupos: Contraste (dos colores enfrentados), Suavidad (todo en una familia) y Momentos del día.
Cada tono da una paleta para la interfaz y una receta para recolorear el fondo (recolour.py)."""
import hashlib
import os
from pathlib import Path

from PySide6.QtGui import QColor, QImage

from .appearance import Palette
from .recolour import recolour

ORIGINAL = 'fondo'
CACHE_VERSION = 1


def _hsl(hue, saturation, lightness):
    return QColor.fromHsl(round(hue) % 360, max(0, min(255, round(saturation))), max(0, min(255, round(lightness)))).name()


def _palette(**roles):
    palette = Palette()
    for role, value in roles.items():
        setattr(palette, role, value)
    return palette


def dark(surface, saturation, accent):
    """Superficies oscuras del tono `surface` y resalte `accent` (hex)."""
    c = lambda s, l: _hsl(surface, saturation * s, l)
    return _palette(base=c(.9, 24), panel=c(.85, 36), card=c(.8, 48), hover=c(.8, 68), border=c(.6, 118),
                    accent=accent, text=c(.5, 234), muted=c(.4, 168), shade=c(1, 13))


def light(surface, saturation, accent):
    """Superficies claras (papel) y texto oscuro."""
    c = lambda s, l: _hsl(surface, saturation * s, l)
    return _palette(base=c(.9, 241), panel=c(.85, 231), card=c(.8, 221), hover=c(.8, 206), border=c(.6, 158),
                    accent=accent, text=c(.6, 30), muted=c(.5, 104), shade=c(1, 248))


def soft(hue, saturation=110):
    """Suavidad: interfaz en una sola familia; el resalte, apenas más vivo."""
    c = lambda s, l: _hsl(hue, saturation * s, l)
    return _palette(base=c(.42, 22), panel=c(.38, 33), card=c(.36, 44), hover=c(.38, 58), border=c(.33, 84),
                    accent=c(.64, 168), text=c(.36, 222), muted=c(.27, 152), shade=c(.5, 14))


same = lambda l: l


def contrast_recipe(accent_hue, surface_hue, accent_sat=1.0, surface_sat=1.0, tint=.12, is_light=False, lift=0.0):
    """La familia principal del fondo toma el resalte; la segunda y los grises, el tono de las superficies."""
    if is_light:
        return ([{'hue': accent_hue, 'sat': accent_sat, 'light': lambda l: .48 + l * .55},
                 {'hue': surface_hue, 'sat': .35 * surface_sat, 'light': lambda l: .66 + l * .5}],
                {'hue': surface_hue, 'sat': .25, 'tint': tint * .7, 'light': lambda l: .74 + l * .5})
    return ([{'hue': accent_hue, 'sat': accent_sat, 'light': lambda l: min(.66, l * (1 + lift) + lift * .1)},
             {'hue': surface_hue, 'sat': surface_sat, 'light': same}],
            {'hue': surface_hue, 'sat': .6 * surface_sat, 'tint': tint, 'light': lambda l: l * 1.1})


def family_recipe(hue, main=.75, second=.35, tint=.10, lift=0.0):
    return ([{'hue': hue, 'sat': main, 'light': lambda l: l + lift * (1 - l) * l * 2},
             {'hue': hue, 'sat': second, 'light': same}],
            {'hue': hue, 'sat': .5, 'tint': tint, 'light': same})


def pair_recipe(first, second, tint_hue, tint=.12, lift=0.0, brighten=1.0):
    """Dos familias del fondo hacia dos tonos dados (amanecer, atardecer…)."""
    return ([{'hue': first, 'sat': .95, 'light': lambda l: min(.7, l * brighten + lift)},
             {'hue': second, 'sat': .8, 'light': lambda l: l * brighten}],
            {'hue': tint_hue, 'sat': .6, 'tint': tint, 'light': lambda l: l * brighten})


class Tone:
    def __init__(self, name, label, group, palette, recipe):
        self.name, self.label, self.group = name, label, group
        self._palette, self.recipe = palette, recipe

    def palette(self):
        return self._palette()


def _tones():
    C, S, M = 'Contraste', 'Suavidad', 'Momentos del día'
    t = [
        # Contraste: superficie y resalte enfrentados.
        Tone('blanco-rojo', 'Blanco y rojo', C, lambda: light(32, 60, '#b3202a'), contrast_recipe(355, 32, is_light=True)),
        Tone('papel-azul', 'Papel y azul tinta', C, lambda: light(40, 50, '#1f4fa0'), contrast_recipe(218, 40, is_light=True)),
        Tone('marron-verde', 'Marrón y verde', C, lambda: dark(25, 95, '#86d06c'), contrast_recipe(105, 25, .7, 1.15, .14, lift=.12)),
        Tone('negro-amarillo', 'Negro y amarillo', C, lambda: dark(0, 0, '#f5c400'), contrast_recipe(46, 0, 1.15, 0, 0, lift=.5)),
        Tone('marino-naranja', 'Azul marino y naranja', C, lambda: dark(220, 120, '#ff8a3d'), contrast_recipe(24, 220, 1.05, .9, .16, lift=.3)),
        Tone('granate-crema', 'Granate y crema', C, lambda: dark(350, 120, '#f0dfb8'), contrast_recipe(42, 350, .45, 1.0, .16, lift=.45)),
        Tone('bosque-dorado', 'Verde bosque y dorado', C, lambda: dark(150, 110, '#e2b84a'), contrast_recipe(44, 150, 1.0, .9, .14, lift=.3)),
        Tone('violeta-menta', 'Violeta y menta', C, lambda: dark(272, 110, '#7fe0b8'), contrast_recipe(155, 272, .8, .9, .16, lift=.3)),
        Tone('carbon-turquesa', 'Carbón y turquesa', C, lambda: dark(200, 25, '#36c9c6'), contrast_recipe(180, 200, 1.0, .2, .04, lift=.3)),
        # Suavidad: todo en una familia.
        Tone('verdes', 'Verdes', S, lambda: soft(135), family_recipe(135)),
        Tone('azules', 'Azules', S, lambda: soft(212), family_recipe(212)),
        Tone('amarillos', 'Amarillos', S, lambda: soft(44), family_recipe(44, .8, .4, .10, .25)),
        Tone('rojos', 'Rojos', S, lambda: soft(352, 100), family_recipe(352)),
        Tone('lavanda', 'Lavanda', S, lambda: soft(268, 90), family_recipe(268, .6, .3)),
        Tone('turquesas', 'Turquesas', S, lambda: soft(180), family_recipe(180)),
        Tone('terracota', 'Terracota', S, lambda: soft(18, 120), family_recipe(18, .8, .4, .12)),
        Tone('rosas', 'Rosas', S, lambda: soft(330, 90), family_recipe(330, .6, .3, .10, .15)),
        Tone('piedra', 'Piedra (grises cálidos)', S, lambda: soft(32, 30), family_recipe(32, .12, .08, .03)),
        # Momentos del día: pensados para el horario de fondos.
        Tone('amanecer', 'Amanecer: melocotón y rosa', M, lambda: dark(345, 70, '#ffb38a'), pair_recipe(22, 340, 345, .14, .06, 1.12)),
        Tone('mediodia', 'Mediodía: claro y cielo', M, lambda: light(45, 40, '#2f7fc8'), contrast_recipe(205, 45, .9, .8, is_light=True)),
        Tone('atardecer', 'Atardecer: naranja y violeta', M, lambda: dark(285, 80, '#ff9a4a'), pair_recipe(26, 290, 300, .16, .08, 1.05)),
        Tone('ocaso', 'Ocaso: rojo fuego y púrpura', M, lambda: dark(320, 90, '#ff6a5a'), pair_recipe(8, 315, 320, .16, .05)),
        Tone('noche', 'Noche: azul profundo y plata', M, lambda: dark(226, 90, '#a9c4ff'), pair_recipe(220, 235, 228, .14, 0, .78)),
    ]
    return {tone.name: tone for tone in t}


TONES = _tones()
GROUPS = ('Contraste', 'Suavidad', 'Momentos del día')


def tone(name):
    return TONES.get(name)


def cache_dir():
    root = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    return root / 'prosperus' / 'fondos'


def toned_wallpaper(path, name, width=1920):
    """Ruta de la imagen `path` recoloreada con el tono `name` (se calcula una vez y se guarda en caché).
    Con el tono original, o si algo falla, devuelve la imagen tal cual."""
    selected = tone(name)
    if path is None or selected is None:
        return path
    path = Path(path)
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return path
    key = hashlib.sha1(f'{path.resolve()}:{stamp}:{name}:{CACHE_VERSION}'.encode()).hexdigest()[:20]
    target = cache_dir() / f'{key}.jpg'
    if target.is_file():
        return target
    image = QImage(str(path))
    if image.isNull():
        return path
    if image.width() > width:
        image = image.scaledToWidth(width)
    targets, neutral = selected.recipe
    result = recolour(image, targets, neutral)[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp.jpg')
    if not result.save(str(temporary), 'JPG', 92):
        return path
    os.replace(temporary, target)
    return target
