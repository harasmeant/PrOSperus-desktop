# SPDX-License-Identifier: GPL-3.0-only
"""Marco de las ventanas a juego con el fondo del proyecto.

El borde lleva el color de resalte (accent) de la paleta que sale del fondo y dos esquinas
opuestas llevan filigrana con el mismo estilo procedural que las ramas del mapa (árbol de la
vida, art déco o art nouveau, según los rasgos del fondo). Lo usan las notas, las ventanas
propias (Ramas, Fondos, Instalador) y los diálogos del escritorio."""
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .branches import branch


def _alpha(colour, value):
    result = QColor(colour); result.setAlphaF(max(0.0, min(1.0, value)))
    return result


def paint_frame(painter, rect, colors, traits=None, radius=12, seed=0, ornate=True):
    """Borde en el color de resalte y filigrana en las esquinas superior izquierda e inferior derecha."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = QRectF(rect)
    accent = QColor(colors.accent)
    # Borde con un degradado suave: más intenso en las esquinas con filigrana.
    sheen = QLinearGradient(rect.topLeft(), rect.bottomRight())
    sheen.setColorAt(0, _alpha(accent, .9)); sheen.setColorAt(.5, _alpha(accent, .38)); sheen.setColorAt(1, _alpha(accent, .9))
    painter.setPen(QPen(sheen, 1.5)); painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(rect, radius, radius)
    if ornate and rect.width() > 160 and rect.height() > 120:
        clip = QPainterPath(); clip.addRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)
        painter.setClipPath(clip)
        length = min(150.0, rect.width() * .24, rect.height() * .34)
        inset = radius * .55 + 3
        vine = _alpha(accent, .78)
        for k, (corner, dx, dy) in enumerate(((rect.topLeft(), 1, 1), (rect.bottomRight(), -1, -1))):
            origin = QPointF(corner.x() + dx * inset, corner.y() + dy * inset)
            # Dos ramas que abrazan la esquina: una por cada borde.
            branch(painter, origin, QPointF(origin.x() + dx * length, origin.y()), 2.0, .5, vine,
                   seed * 4 + k * 2 + 1, 2, .06, traits)
            branch(painter, origin, QPointF(origin.x(), origin.y() + dy * length * .8), 2.0, .5, vine,
                   seed * 4 + k * 2 + 2, 2, .06, traits)
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(_alpha(accent, .8))
            painter.drawEllipse(origin, 2.8, 2.8)
    painter.restore()


class FrameOverlay(QWidget):
    """Capa transparente encima de una ventana que dibuja su marco; no recibe el ratón.

    colors() y traits() se consultan al pintar: si el proyecto cambia, el marco también."""

    def __init__(self, window, colors, traits=lambda: None, radius=10, seed=0):
        super().__init__(window)
        self.colors, self.traits, self.radius, self.seed = colors, traits, radius, seed
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.follower = _Follower(self)
        window.installEventFilter(self.follower)
        self.setGeometry(window.rect()); self.raise_(); self.show()

    def paintEvent(self, event):
        colors = self.colors()
        if colors is None:
            return
        painter = QPainter(self)
        paint_frame(painter, QRectF(self.rect()).adjusted(1, 1, -1, -1), colors, self.traits(), self.radius, self.seed)


class _Follower(QObject):
    """Mantiene la capa del tamaño de la ventana y por encima de sus hijos."""

    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.overlay.setGeometry(watched.rect()); self.overlay.raise_()
        elif event.type() == QEvent.Type.ChildAdded:
            self.overlay.raise_()
        return False


def attach_frame(window, colors, traits=lambda: None, radius=10):
    """Pone el marco a una ventana una sola vez. Devuelve la capa."""
    existing = getattr(window, '_prosperus_frame', None)
    if existing is not None:
        return existing
    window._prosperus_frame = FrameOverlay(window, colors, traits, radius, len(window.windowTitle()))
    return window._prosperus_frame
