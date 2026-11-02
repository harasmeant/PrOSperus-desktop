"""Botones de ventana discretos: tres puntos que crecen al pasar el ratón."""
# SPDX-License-Identifier: GPL-3.0-only
from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

# (acción, color, nombre accesible); el orden es el de izquierda a derecha.
BUTTONS = [('minimize', '#e6b450', 'Minimizar'), ('maximize', '#7fbf6a', 'Ampliar'),
           ('close', '#e06c62', 'Cerrar')]
SMALL, LARGE, GAP = 8, 22, 6
PAD = 5  # margen para el anillo del botón bajo el ratón
REST = QColor(138, 147, 132)  # gris verdoso de los puntos en reposo


class HoverControls(QWidget):
    """Puntos pequeños en reposo; al pasar el ratón por la ventana (o por ellos) se agrandan con símbolo.

    `watch` es el widget cuyo «hover» despliega los botones; por defecto, ellos mismos.
    Emite `triggered` con 'minimize', 'maximize' o 'close'.
    """
    triggered = Signal(str)

    def __init__(self, parent=None, watch=None, actions=('minimize', 'maximize', 'close')):
        super().__init__(parent)
        self.buttons = [b for b in BUTTONS if b[0] in actions]
        self.progress = 0.0  # 0 = puntos, 1 = botones completos
        self.hovered = None
        self.pressed = None  # acción pulsada; solo se dispara al soltar sobre ella
        self.maximized = False
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Controles de ventana')
        self.setToolTip(' · '.join(b[2] for b in self.buttons))
        self.animation = QVariantAnimation(self, duration=140)
        self.animation.valueChanged.connect(self._set_progress)
        self.setFixedSize(self.sizeHint())
        self.watched = watch or self
        if self.watched is not self:
            self.watched.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            self.watched.installEventFilter(self)

    def sizeHint(self):
        n = len(self.buttons)
        return QSize(n * LARGE + (n - 1) * GAP + 2 * PAD, LARGE + 2 * PAD)

    def expanded(self):
        return self.progress > .5

    def expand(self, on):
        target = 1.0 if on else 0.0
        if self.animation.endValue() == target and self.animation.state() == QVariantAnimation.State.Running:
            return
        self.animation.stop()
        self.animation.setStartValue(self.progress); self.animation.setEndValue(target)
        self.animation.start()

    def set_maximized(self, on):
        """Con la ventana ampliada, el botón central pasa a «Restaurar»."""
        if self.maximized == bool(on):
            return
        self.maximized = bool(on)
        self._update_tooltip(); self.update()

    def _name(self, action, name):
        return 'Restaurar' if action == 'maximize' and self.maximized else name

    def _update_tooltip(self):
        names = [self._name(a, n) for a, _, n in self.buttons if self.hovered in (None, a)]
        self.setToolTip(' · '.join(names))

    def _set_progress(self, value):
        self.progress = float(value); self.update()

    def eventFilter(self, obj, event):
        if obj is self.watched:
            if event.type() in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
                self.expand(True)
            elif event.type() in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
                self.expand(False)
        return False

    def enterEvent(self, event):
        self.expand(True)

    def leaveEvent(self, event):
        self.hovered = self.pressed = None
        self._update_tooltip()
        if self.watched is self or not self.watched.underMouse():
            self.expand(False)
        self.update()

    def _rects(self):
        size = SMALL + (LARGE - SMALL) * self.progress
        y = (self.height() - size) / 2
        right = self.width() - PAD
        rects = []
        for i in reversed(range(len(self.buttons))):
            # Cada botón conserva su hueco de tamaño completo: crecer no desplaza a los demás.
            cx = right - LARGE / 2 - (len(self.buttons) - 1 - i) * (LARGE + GAP)
            rects.insert(0, QRectF(cx - size / 2, y, size, size))
        return rects

    def action_at(self, pos):
        for (action, _, _), rect in zip(self.buttons, self._rects()):
            if rect.adjusted(-3, -3, 3, 3).contains(pos):
                return action
        return None

    def mouseMoveEvent(self, event):
        hovered = self.action_at(event.position())
        if hovered != self.hovered:
            self.hovered = hovered; self._update_tooltip(); self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed = self.action_at(event.position()); self.update()
        event.accept()  # que el clic no empiece a arrastrar la ventana

    def mouseReleaseEvent(self, event):
        action = self.action_at(event.position())
        pressed, self.pressed = self.pressed, None
        self.update()
        # Soltar fuera del botón pulsado cancela, como en cualquier botón.
        # En reposo los puntos también responden: no hace falta esperar a la animación.
        if event.button() == Qt.MouseButton.LeftButton and action and action == pressed:
            self.triggered.emit(action)
        event.accept()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.progress
        for (action, color, _), rect in zip(self.buttons, self._rects()):
            own = QColor(color)
            if action == self.hovered:
                fill = own
                ring = QColor(own); ring.setAlphaF(.35)
                p.setPen(QPen(ring, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(rect.adjusted(-3, -3, 3, 3))
            else:
                # En reposo, gris discreto; al desplegarse, el color propio del botón.
                fill = QColor.fromRgbF(REST.redF() + (own.redF() - REST.redF()) * t,
                                       REST.greenF() + (own.greenF() - REST.greenF()) * t,
                                       REST.blueF() + (own.blueF() - REST.blueF()) * t, .6 + .4 * t)
            if action == self.pressed:
                fill = fill.darker(115)
                d = rect.width() * .06
                rect = rect.adjusted(d, d, -d, -d)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(fill); p.drawEllipse(rect)
            if t < .35:
                continue
            ink = QColor('#1b1d1a'); ink.setAlphaF(min(1.0, (t - .35) / .5))
            p.setPen(QPen(ink, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            m = rect.width() * .3
            inner = rect.adjusted(m, m, -m, -m)
            if action == 'minimize':
                p.drawLine(inner.left(), inner.center().y(), inner.right(), inner.center().y())
            elif action == 'maximize' and self.maximized:
                # Restaurar: dos ventanas superpuestas; de la de atrás solo asoma el borde.
                k = inner.width() * .3
                front = inner.adjusted(0, k, -k, 0)
                p.drawLine(front.left() + k, inner.top(), inner.right(), inner.top())
                p.drawLine(inner.right(), inner.top(), inner.right(), front.bottom() - k)
                p.drawLine(front.left() + k, inner.top(), front.left() + k, front.top())
                p.drawLine(front.right(), front.bottom() - k, inner.right(), front.bottom() - k)
                p.drawRect(front)
            elif action == 'maximize':
                p.drawRect(inner)
            else:
                p.drawLine(inner.topLeft(), inner.bottomRight()); p.drawLine(inner.topRight(), inner.bottomLeft())
