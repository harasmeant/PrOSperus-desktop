# SPDX-License-Identifier: GPL-3.0-only
"""Marco de las ventanas a juego con el fondo del proyecto.

Sin línea de borde: dos esquinas
opuestas llevan filigrana con el mismo estilo procedural que las ramas del mapa (árbol de la
vida, art déco o art nouveau, según los rasgos del fondo). Lo usan las notas, las ventanas
propias (Ramas, Fondos, Instalador) y los diálogos del escritorio."""
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QRegion
from PySide6.QtWidgets import QMainWindow, QWidget

from .branches import branch

MARGIN = 22  # margen mínimo del contenido dentro del marco
GRIP = 18    # franja junto al borde que agranda o achica la ventana (Wayland: solo por dentro)


def paint_frame(painter, rect, colors, traits=None, radius=12, seed=0, ornate=True):
    """Filigrana en el color de resalte en las esquinas superior izquierda e inferior derecha (sin línea de borde)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = QRectF(rect)
    accent = QColor(colors.accent)
    if ornate and rect.width() > 160 and rect.height() > 120:
        clip = QPainterPath(); clip.addRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)
        painter.setClipPath(clip)
        length = min(150.0, rect.width() * .24, rect.height() * .34)
        inset = radius * .55 + 3
        vine = accent
        for k, (corner, dx, dy) in enumerate(((rect.topLeft(), 1, 1), (rect.bottomRight(), -1, -1))):
            origin = QPointF(corner.x() + dx * inset, corner.y() + dy * inset)
            # Dos ramas que abrazan la esquina: una por cada borde.
            branch(painter, origin, QPointF(origin.x() + dx * length, origin.y()), 2.0, .5, vine,
                   seed * 4 + k * 2 + 1, 2, .06, traits)
            branch(painter, origin, QPointF(origin.x(), origin.y() + dy * length * .8), 2.0, .5, vine,
                   seed * 4 + k * 2 + 2, 2, .06, traits)
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(accent)
            painter.drawEllipse(origin, 2.8, 2.8)
    painter.restore()


class FrameOverlay(QWidget):
    """Capa transparente encima de una ventana que dibuja su marco; no recibe el ratón.

    colors() y traits() se consultan al pintar: si el proyecto cambia, el marco también."""

    # Crea marco con filigrana en esquinas y color de resalte
    def __init__(self, window, colors, traits=lambda: None, radius=10, seed=0):
        super().__init__(window)
        self.colors, self.traits, self.radius, self.seed = colors, traits, radius, seed
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.grip = _ResizeGrip(window)
        self.follower = _Follower(self)
        window.installEventFilter(self.follower)
        self.setGeometry(window.rect()); self.raise_(); self.grip.fit(); self.show()

    # Dibuja marco con colores y patrones procedurales
    def paintEvent(self, event):
        colors = self.colors()
        if colors is None:
            return
        painter = QPainter(self)
        paint_frame(painter, QRectF(self.rect()).adjusted(1, 1, -1, -1), colors, self.traits(), self.radius, self.seed)


def grip_edges(pos, size, grip=GRIP):
    """Bordes (Qt.Edge) bajo `pos` en una ventana de tamaño `size`; vacío si no está en la franja."""
    edges = Qt.Edge(0)
    if pos.x() < grip: edges |= Qt.Edge.LeftEdge
    if pos.x() >= size.width() - grip: edges |= Qt.Edge.RightEdge
    if pos.y() < grip: edges |= Qt.Edge.TopEdge
    if pos.y() >= size.height() - grip: edges |= Qt.Edge.BottomEdge
    return edges


_CURSORS = {Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor, Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
            Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor, Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
            Qt.Edge.TopEdge | Qt.Edge.LeftEdge: Qt.CursorShape.SizeFDiagCursor,
            Qt.Edge.BottomEdge | Qt.Edge.RightEdge: Qt.CursorShape.SizeFDiagCursor,
            Qt.Edge.TopEdge | Qt.Edge.RightEdge: Qt.CursorShape.SizeBDiagCursor,
            Qt.Edge.BottomEdge | Qt.Edge.LeftEdge: Qt.CursorShape.SizeBDiagCursor}


class _ResizeGrip(QWidget):
    """Franja invisible por dentro del borde (máscara en anillo): arrastrarla agranda o achica la ventana."""

    def __init__(self, window):
        super().__init__(window)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def fit(self):
        rect = self.parentWidget().rect()
        self.setGeometry(rect)
        self.setMask(QRegion(rect).subtracted(QRegion(rect.adjusted(GRIP, GRIP, -GRIP, -GRIP))))
        self.raise_(); self.show()

    def mouseMoveEvent(self, event):
        edges = grip_edges(event.position().toPoint(), self.size())
        self.setCursor(_CURSORS.get(edges, Qt.CursorShape.ArrowCursor))

    def mousePressEvent(self, event):
        edges = grip_edges(event.position().toPoint(), self.size())
        handle = self.window().windowHandle()
        if event.button() == Qt.MouseButton.LeftButton and edges and handle is not None:
            handle.startSystemResize(edges)


class _Follower(QObject):
    """Mantiene la capa del tamaño de la ventana y por encima de sus hijos."""

    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay

    # Sincronizar overlay con eventos de ventana
    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.overlay.setGeometry(watched.rect()); self.overlay.raise_(); self.overlay.grip.fit()
        elif event.type() == QEvent.Type.ChildAdded:
            self.overlay.raise_(); self.overlay.grip.raise_()
        return False


def attach_frame(window, colors, traits=lambda: None, radius=10):
    """Pone el marco a una ventana una sola vez. Devuelve la capa."""
    existing = getattr(window, '_prosperus_frame', None)
    if existing is not None:
        return existing
    window._prosperus_frame = FrameOverlay(window, colors, traits, radius, len(window.windowTitle()))
    make_room(window)
    return window._prosperus_frame


def make_room(window, side=MARGIN, top=12):
    """Deja margen para que la filigrana de las esquinas no pise los botones."""
    holder = window.centralWidget() if isinstance(window, QMainWindow) else window
    layout = holder.layout() if holder is not None else None
    if layout is None:
        return
    m = layout.contentsMargins()
    layout.setContentsMargins(max(m.left(), side), max(m.top(), top), max(m.right(), side), max(m.bottom(), side))
