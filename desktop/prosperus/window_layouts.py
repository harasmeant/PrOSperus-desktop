"""Geometría compartida por notas, previsualización y ventanas del compositor.

Las coordenadas son lógicas: el escalado del monitor lo aplica Wayland/Qt.
El motor no abre aplicaciones ni cambia la configuración de las pantallas.
"""
# SPDX-License-Identifier: GPL-3.0-only
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class LayoutOptions:
    mode: str = 'spiral'
    gap: int = 12
    ratio: int = 50
    max_width: int = 0

    def validate(self):
        if self.mode not in ('spiral', 'columns', 'centered'):
            raise ValueError('Distribución desconocida.')
        if not 0 <= self.gap <= 48 or not 30 <= self.ratio <= 70:
            raise ValueError('Separación o proporción fuera de rango.')
        if not 0 <= self.max_width <= 10000:
            raise ValueError('Anchura de trabajo fuera de rango.')


def screen_profile(width, height):
    aspect = width / max(1, height)
    return 'superwide' if aspect >= 3 else 'ultrawide' if aspect >= 2.1 else 'standard'


def arrange(area, count, options, minimum=(320, 220)):
    """Devuelve rectángulos sin solapes o rechaza la operación completa.

    No se apilan ventanas silenciosamente cuando falta espacio. El consumidor
    puede conservar la disposición previa y ofrecer menos ventanas/otra vista.
    """
    options.validate()
    if count < 0 or count > 64:
        raise ValueError('Se admiten hasta 64 ventanas por distribución.')
    if count == 0:
        return []
    g = options.gap
    width = min(area.width, options.max_width) if options.max_width else area.width
    work = Rect(area.x + (area.width - width) // 2 + g, area.y + g,
                width - 2 * g, area.height - 2 * g)

    def columns(rect, n):
        available = rect.width - g * (n - 1)
        return [Rect(rect.x + i * available // n + i * g, rect.y,
                     (i + 1) * available // n - i * available // n, rect.height)
                for i in range(n)]

    def rows(rect, n):
        available = rect.height - g * (n - 1)
        return [Rect(rect.x, rect.y + i * available // n + i * g, rect.width,
                     (i + 1) * available // n - i * available // n)
                for i in range(n)] if n else []

    if count == 1:
        result = [work]
    elif options.mode == 'columns':
        result = columns(work, count)
    elif options.mode == 'centered' and count > 2:
        middle = round((work.width - 2 * g) * options.ratio / 100)
        side = (work.width - middle - 2 * g) // 2
        result = [Rect(work.x + side + g, work.y, middle, work.height)]
        result += rows(Rect(work.x, work.y, side, work.height), math.ceil((count - 1) / 2))
        result += rows(Rect(work.x + side + middle + 2 * g, work.y,
                            work.width - side - middle - 2 * g, work.height), (count - 1) // 2)
    else:
        # Fibonacci: izquierda, arriba, derecha, abajo; cada corte consume la
        # mitad del espacio restante. Solo el primer corte admite otra proporción.
        result, rest = [], work
        for i in range(count - 1):
            fraction = options.ratio / 100 if i == 0 else .5
            if i % 2 == 0:
                size = round((rest.width - g) * fraction)
                if i % 4 == 0:
                    result.append(Rect(rest.x, rest.y, size, rest.height))
                    rest = Rect(rest.x + size + g, rest.y, rest.width - size - g, rest.height)
                else:
                    result.append(Rect(rest.x + rest.width - size, rest.y, size, rest.height))
                    rest = Rect(rest.x, rest.y, rest.width - size - g, rest.height)
            else:
                size = round((rest.height - g) * fraction)
                if i % 4 == 1:
                    result.append(Rect(rest.x, rest.y, rest.width, size))
                    rest = Rect(rest.x, rest.y + size + g, rest.width, rest.height - size - g)
                else:
                    result.append(Rect(rest.x, rest.y + rest.height - size, rest.width, size))
                    rest = Rect(rest.x, rest.y, rest.width, rest.height - size - g)
        result.append(rest)
    if any(r.width < minimum[0] or r.height < minimum[1] for r in result):
        raise ValueError('No caben con un tamaño legible. Reduce ventanas, amplía el área o cambia la distribución.')
    return result
