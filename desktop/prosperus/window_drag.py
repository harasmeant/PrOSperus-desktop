# SPDX-License-Identifier: GPL-3.0-only
"""Detecta cuándo se suelta una ventana flotante tras arrastrarla.

Sway no avisa por IPC mientras se arrastra una ventana flotante ni dice cuándo se suelta el
botón: se deduce de la geometría. Una ventana que cambia de posición sin cambiar de tamaño en
lecturas seguidas se está arrastrando; cuando se queda quieta un momento, se ha soltado.

Al soltarla queda libre donde está y las demás cierran el hueco (window_manager.py)."""
from collections import deque
from dataclasses import dataclass

STILL = 0.35        # s sin moverse = soltada
MIN_STEPS = 2       # lecturas con movimiento para ser un arrastre (una sola es un salto por teclado/IPC)
WINDOW = 0.15       # s de muestras para medir la velocidad final
MAX_SPEED = 6000    # px/s; más es ruido (un salto entre lecturas)


@dataclass(frozen=True)
class Drop:
    con_id: int
    rect: tuple          # (x, y, ancho, alto) al soltar
    area: tuple          # (x, y, ancho, alto) del espacio de trabajo
    output: str
    velocity: tuple      # px/s


class DragTracker:
    """Se le dan lecturas de geometría (`feed`) y devuelve las ventanas soltadas tras un arrastre."""

    def __init__(self):
        self.last = {}           # con_id -> (x, y, w, h)
        self.last_time = None    # momento de la lectura anterior
        self.drags = {}          # con_id -> {'samples': deque[(t, x, y)], 'steps', 'moved_at', 'area', 'output'}

    @property
    def active(self):
        return bool(self.drags)

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
