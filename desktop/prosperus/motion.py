# SPDX-License-Identifier: GPL-3.0-only
"""Animaciones suaves y reutilizables del escritorio.

Borrador de qwen2.5-coder (local), revisado: animaciones que se pisan y widgets borrados a mitad."""
from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, QAbstractAnimation, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


def fade_in(widgets, duration=220, stagger=30, on_step=None):
    """on_step: se llama en cada fotograma (p. ej. para repintar lo que depende de la opacidad)."""
    for i, widget in enumerate(widgets):
        if widget is None:
            continue
        previous = getattr(widget, '_fade', None)
        if previous is not None:
            previous.stop()  # sin «finished»: no quita el efecto nuevo
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b'opacity', widget)
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda w=widget: w.setGraphicsEffect(None))
        if on_step is not None:
            animation.valueChanged.connect(lambda *_: on_step())
            animation.finished.connect(on_step)
        # Con contexto: si el widget desaparece antes de empezar, no se llama.
        QTimer.singleShot(i * stagger, animation, animation.start)
        widget._fade = animation

# Animar widgets suavemente hacia el escritorio
def slide_in(widget, offset, duration=260):
    previous = getattr(widget, '_slide', None)
    if previous is not None and previous.state() == QAbstractAnimation.State.Running:
        previous.stop(); widget.move(previous.endValue())  # parte del destino, no de medio camino
    end = widget.pos()
    start = end + offset
    widget.move(start)
    animation = QPropertyAnimation(widget, b'pos', widget)
    animation.setDuration(duration)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    widget._slide = animation
    animation.start()
    return animation

# Desaparición suave de widget con efecto fantasma
def ghost_out(widget, offset, duration=180):
    # QWidget.hide directo: funciona aunque la clase sobrescriba hide() para llamar aquí.
    if widget.parentWidget() is None or not widget.isVisible():
        QWidget.hide(widget)
        return None
    pixmap = widget.grab()
    ghost = QLabel(widget.parentWidget())
    ghost.setPixmap(pixmap)
    ghost.setGeometry(widget.geometry())
    ghost.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    ghost.show()
    ghost.raise_()
    QWidget.hide(widget)
    animation = QPropertyAnimation(ghost, b'pos', ghost)
    animation.setDuration(duration)
    animation.setStartValue(ghost.pos())
    animation.setEndValue(ghost.pos() + offset)
    animation.setEasingCurve(QEasingCurve.Type.InCubic)
    animation.finished.connect(ghost.deleteLater)
    animation.start()
    return animation
