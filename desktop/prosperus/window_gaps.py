# SPDX-License-Identifier: GPL-3.0-only
"""Huecos entre aplicaciones: arrastrar para deformarlas y doble clic para minimizarlas.

El escritorio está debajo de las aplicaciones flotantes, así que los clics en el hueco que
las separa (la «separación» de Fibonacci) le llegan a él. Con el árbol de Sway se sabe qué
bordes tocan ese hueco: arrastrar mueve ese borde en todas las ventanas que lo comparten,
como el separador de un mosaico. Doble clic en el fondo minimiza las aplicaciones del proyecto.
"""
from dataclasses import dataclass, replace

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSlider, QAbstractSpinBox, QApplication,
                               QComboBox, QLineEdit, QPlainTextEdit, QTextEdit, QWidget)

from .window_layouts import Rect
from .window_session import DESKTOP_ID, SHELL_IDS, request, walk

# Lo más pequeño que se deja una ventana al deformarla (algo menos que al organizar).
MINIMUM = (200, 140)


@dataclass(frozen=True)
class Splitter:
    """Borde que se arrastra. vertical: línea de arriba abajo (cambia anchuras)."""
    vertical: bool
    before: tuple  # ids de las ventanas a la izquierda (o arriba) del hueco
    after: tuple   # ids de las ventanas a la derecha (o abajo)


def _span(r, vertical):
    """(inicio, fin) en el eje que recorre la línea del hueco."""
    return (r.y, r.y + r.height) if vertical else (r.x, r.x + r.width)


def _edges(r, vertical):
    """(borde final, borde inicial) en el eje que cruza el hueco."""
    return (r.x + r.width, r.x) if vertical else (r.y + r.height, r.y)


def _line(rects, x, y, band, vertical):
    along, across = (y, x) if vertical else (x, y)
    before = [i for i, r in rects.items() if across - band <= _edges(r, vertical)[0] <= across
              and _span(r, vertical)[0] - band <= along <= _span(r, vertical)[1] + band]
    after = [i for i, r in rects.items() if across <= _edges(r, vertical)[1] <= across + band
             and _span(r, vertical)[0] - band <= along <= _span(r, vertical)[1] + band]
    if not before and not after:
        return None
    # El punto tiene que estar a la altura de alguna ventana, no solo cerca de su esquina.
    if not any(_span(rects[i], vertical)[0] <= along <= _span(rects[i], vertical)[1] for i in before + after):
        return None
    # Toda la línea: ventanas con el mismo borde que se tocan a lo largo del hueco.
    edge_before = {_edges(rects[i], vertical)[0] for i in before}
    edge_after = {_edges(rects[i], vertical)[1] for i in after}
    groups = [set(before), set(after)]
    low = min(_span(rects[i], vertical)[0] for i in before + after)
    high = max(_span(rects[i], vertical)[1] for i in before + after)
    grown = True
    while grown:
        grown = False
        for i, r in rects.items():
            if i in groups[0] or i in groups[1]:
                continue
            start, end = _span(r, vertical)
            if end < low - band or start > high + band:
                continue
            for group, edges, edge in ((0, edge_before, _edges(r, vertical)[0]), (1, edge_after, _edges(r, vertical)[1])):
                if any(abs(edge - e) <= 2 for e in edges):
                    groups[group].add(i); low, high = min(low, start), max(high, end); grown = True
                    break
    return Splitter(vertical, tuple(sorted(groups[0])), tuple(sorted(groups[1])))


def find_splitter(rects, x, y, gap):
    """Borde que hay bajo el punto (x, y), o None si el punto no está en un hueco junto a una ventana."""
    band = max(gap, 6) + 6
    return _line(rects, x, y, band, True) or _line(rects, x, y, band, False)


def drag(rects, splitter, delta, area, minimum=MINIMUM):
    """Nuevos rectángulos al mover el borde `delta` px; se limita para no bajar del mínimo ni salir del área."""
    v = splitter.vertical
    size = 'width' if v else 'height'
    pos = 'x' if v else 'y'
    smallest = minimum[0] if v else minimum[1]
    low, high = -10 ** 6, 10 ** 6
    for i in splitter.before:
        low = max(low, smallest - getattr(rects[i], size))
    for i in splitter.after:
        high = min(high, getattr(rects[i], size) - smallest)
    area_start, area_end = (area.x, area.x + area.width) if v else (area.y, area.y + area.height)
    if not splitter.after:
        high = min(high, min(area_end - _edges(rects[i], v)[0] for i in splitter.before))
    if not splitter.before:
        low = max(low, max(area_start - _edges(rects[i], v)[1] for i in splitter.after))
    delta = max(low, min(high, delta)) if low <= high else 0
    result = {}
    for i in splitter.before:
        result[i] = replace(rects[i], **{size: getattr(rects[i], size) + delta})
    for i in splitter.after:
        result[i] = replace(rects[i], **{pos: getattr(rects[i], pos) + delta, size: getattr(rects[i], size) - delta})
    return result


def commands_for(rects):
    return '; '.join(f'[con_id={i}] resize set width {r.width} px height {r.height} px, '
                     f'move absolute position {r.x} px {r.y} px' for i, r in sorted(rects.items()))


def is_background(widget, stop):
    """El clic cae en el fondo del escritorio, no en una tarjeta, un botón o un campo de texto."""
    from .shell import MapNode, NotePanel
    controls = (QAbstractButton, QLineEdit, QTextEdit, QPlainTextEdit, QAbstractItemView,
                QAbstractSlider, QAbstractSpinBox, QComboBox, MapNode, NotePanel)
    while widget is not None and widget is not stop:
        if isinstance(widget, controls):
            return False
        widget = widget.parentWidget()
    return True


class GapControl(QObject):
    """Filtro de eventos del escritorio para los huecos entre aplicaciones (solo con Sway)."""

    def __init__(self, shell):
        super().__init__(shell)
        self.shell = shell
        self.active = None  # (splitter, rects, área, punto de partida) mientras se arrastra
        self.pending = None
        self.last_event = None
        self.timer = QTimer(self, interval=33, singleShot=True, timeout=self.flush)
        QApplication.instance().installEventFilter(self)

    def visible_windows(self):
        return any(not w.get('hidden') for w in self.shell.app_windows)

    def layout(self):
        """(posición del escritorio, rectángulos de las aplicaciones de su espacio, área del espacio)."""
        tree = request(4)
        for ws in walk(tree):
            if ws.get('type') != 'workspace':
                continue
            nodes = list(walk(ws))
            desk = next((n for n in nodes if n.get('app_id') == DESKTOP_ID and n.get('name') == 'PrOSperus desktop'), None)
            if desk is None:
                continue
            rects = {n['id']: Rect(**{k: n['rect'][k] for k in ('x', 'y', 'width', 'height')}) for n in nodes
                     if n.get('type') == 'floating_con' and (n.get('app_id') or n.get('window'))
                     and n.get('app_id') not in SHELL_IDS and not n.get('fullscreen_mode')
                     and (n.get('window_properties') or {}).get('class') != DESKTOP_ID}
            return QPoint(desk['rect']['x'], desk['rect']['y']), rects, Rect(**ws['rect'])
        return None

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind not in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove,
                        QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick):
            return False
        if self.active is not None:
            if kind == QEvent.Type.MouseMove:
                splitter, rects, area, start = self.active
                point = event.globalPosition().toPoint()
                delta = (point - start).x() if splitter.vertical else (point - start).y()
                self.pending = drag(rects, splitter, delta, area)
                if not self.timer.isActive():
                    self.timer.start()
            elif kind == QEvent.Type.MouseButtonRelease:
                self.timer.stop(); self.flush()
                self.active = None
                QApplication.restoreOverrideCursor()
            return True
        # Cada evento pasa por el filtro una vez por widget al subir hacia el padre: solo el primero.
        if not self.shell.windows.available or not isinstance(obj, QWidget) or obj.window() is not self.shell:
            return False
        key = (kind, event.timestamp(), event.globalPosition().toPoint().toTuple())
        if key == self.last_event:
            return False
        self.last_event = key
        if event.button() != Qt.MouseButton.LeftButton or not self.visible_windows():
            return False
        if kind == QEvent.Type.MouseButtonDblClick:
            if is_background(obj, self.shell):
                self.shell.windows.minimize_all()
                return True
            return False
        if kind != QEvent.Type.MouseButtonPress or not is_background(obj, self.shell):
            return False
        try:
            found = self.layout()
        except (OSError, ValueError, KeyError, TypeError):
            return False
        if not found:
            return False
        origin, rects, area = found
        local = self.shell.mapFromGlobal(event.globalPosition().toPoint())
        x, y = origin.x() + local.x(), origin.y() + local.y()
        splitter = find_splitter(rects, x, y, self.shell.layout_options().gap)
        if splitter is None:
            return False
        self.active = (splitter, rects, area, event.globalPosition().toPoint())
        QApplication.setOverrideCursor(Qt.CursorShape.SplitHCursor if splitter.vertical else Qt.CursorShape.SplitVCursor)
        return True

    def flush(self):
        rects, self.pending = self.pending, None
        if not rects:
            return
        try:
            request(0, commands_for(rects))
        except (OSError, ValueError) as error:
            self.shell.status.setText(f'No se pudo cambiar el tamaño: {error}')
