# SPDX-License-Identifier: GPL-3.0-only
"""Arrastrar una ventana al centro de la pantalla la mete en el patrón de Fibonacci.

Sway no avisa por IPC mientras se arrastra una ventana flotante ni dice cuándo se suelta el
botón: se deduce de la geometría. Una ventana que cambia de posición sin cambiar de tamaño en
lecturas seguidas se está arrastrando; cuando se queda quieta un momento, se ha soltado.

Al soltarla se mira dónde ha quedado su centro y adónde iba (la velocidad de los últimos
instantes, como si siguiera por inercia): si cae en la zona central de la pantalla, ocupa la
siguiente posición del patrón y la ventana que estaba al final se reduce a la mitad para hacerle
sitio. Si se suelta fuera, queda libre donde está y las demás cierran el hueco."""
from collections import deque
from dataclasses import dataclass

STILL = 0.35        # s sin moverse = soltada
MIN_STEPS = 2       # lecturas con movimiento para ser un arrastre (una sola es un salto por teclado/IPC)
WINDOW = 0.15       # s de muestras para medir la velocidad final
GLIDE = 0.25        # s de inercia: un lanzamiento hacia el centro también cuenta
ZONE = 0.40         # la zona central ocupa este tanto del ancho y del alto de la pantalla
MAX_SPEED = 6000    # px/s; más es ruido (un salto entre lecturas)


@dataclass(frozen=True)
class Drop:
    con_id: int
    rect: tuple          # (x, y, ancho, alto) al soltar
    area: tuple          # (x, y, ancho, alto) del espacio de trabajo
    output: str
    velocity: tuple      # px/s


def central_zone(area, share=ZONE):
    x, y, w, h = area
    zw, zh = w * share, h * share
    return (x + (w - zw) / 2, y + (h - zh) / 2, zw, zh)


def inside(point, rect):
    return rect[0] <= point[0] <= rect[0] + rect[2] and rect[1] <= point[1] <= rect[1] + rect[3]


def projected_centre(rect, velocity, glide=GLIDE):
    cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
    return cx + velocity[0] * glide, cy + velocity[1] * glide


def joins_pattern(drop, share=ZONE):
    """¿Entra en el patrón? Por dónde ha quedado o por adónde iba."""
    zone = central_zone(drop.area, share)
    centre = projected_centre(drop.rect, (0, 0))
    return inside(centre, zone) or inside(projected_centre(drop.rect, drop.velocity), zone)


class DragTracker:
    """Se le dan lecturas de geometría (`feed`) y devuelve las ventanas soltadas tras un arrastre."""

    def __init__(self):
        self.last = {}           # con_id -> (x, y, w, h)
        self.last_time = None    # momento de la lectura anterior
        self.drags = {}          # con_id -> {'samples': deque[(t, x, y)], 'steps', 'moved_at', 'area', 'output'}

    @property
    def active(self):
        return bool(self.drags)

    def dragging(self):
        """{con_id: (rect, area, output, velocity)} de los arrastres en curso que ya son arrastres."""
        return {i: (self.last[i], d['area'], d['output'], velocity(d['samples']))
                for i, d in self.drags.items() if d['steps'] >= MIN_STEPS and i in self.last}

    def reset(self, windows=None):
        """Olvida los arrastres (p. ej. tras organizar: esos movimientos no son del usuario)."""
        self.drags.clear()
        self.last = {i: w[0] for i, w in (windows or {}).items()}
        self.last_time = None

    def feed(self, now, windows):
        """windows: {con_id: (rect, area, output)}. Devuelve [Drop] de las ventanas recién soltadas."""
        drops, before = [], self.last_time if self.last_time is not None else now
        self.last_time = now
        for con_id, (rect, area, output) in windows.items():
            previous = self.last.get(con_id)
            self.last[con_id] = rect
            drag = self.drags.get(con_id)
            if previous is None:
                continue
            moved = rect[:2] != previous[:2]
            if rect[2:] != previous[2:]:
                # Cambio de tamaño: redimensionar u organizar, no es arrastrar.
                self.drags.pop(con_id, None)
                continue
            if moved:
                if drag is None:
                    drag = self.drags[con_id] = {'samples': deque([(before, previous[0], previous[1])], maxlen=32),
                                                 'steps': 0}
                drag['samples'].append((now, rect[0], rect[1]))
                drag['steps'] += 1
                drag['moved_at'] = now
                drag['area'], drag['output'] = area, output
            elif drag is not None and now - drag['moved_at'] >= STILL:
                del self.drags[con_id]
                if drag['steps'] >= MIN_STEPS:
                    drops.append(Drop(con_id, rect, area, output, velocity(drag['samples'])))
        for con_id in [i for i in self.last if i not in windows]:
            # Cerrada o en otro espacio.
            self.last.pop(con_id); self.drags.pop(con_id, None)
        return drops


def velocity(samples, window=WINDOW):
    """px/s de las muestras de los últimos `window` s antes del último movimiento."""
    if len(samples) < 2:
        return (0.0, 0.0)
    end = samples[-1]
    start = next((s for s in samples if end[0] - s[0] <= window), samples[0])
    if start is end:
        start = samples[-2]
    dt = end[0] - start[0]
    if dt <= 0:
        return (0.0, 0.0)
    clamp = lambda v: max(-MAX_SPEED, min(MAX_SPEED, v))
    return (clamp((end[1] - start[1]) / dt), clamp((end[2] - start[2]) / dt))
