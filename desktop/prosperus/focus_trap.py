# SPDX-License-Identifier: GPL-3.0-only
"""Tabulador dentro de una ventana del escritorio (notas, tarjetero, panel Sistema)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget


def focus_chain(container):
    """Return the widgets inside `container` that Tab can reach, in Tab order."""
    w = container.nextInFocusChain()
    widgets = []
    for _ in range(2000):
        if w is container:
            break
        if container.isAncestorOf(w) and w.isVisible() and w.isEnabled() and (w.focusPolicy() & Qt.FocusPolicy.TabFocus) == Qt.FocusPolicy.TabFocus and w.focusProxy() is None:
            if w not in widgets:
                widgets.append(w)
        w = w.nextInFocusChain()
    return widgets


def cycle_focus(container, forward):
    """Tab/Shift+Tab inside container: move focus and wrap around. Return True if handled."""
    widgets = focus_chain(container)
    if not widgets:
        return False
    current = QApplication.focusWidget()
    if current in widgets:
        i = widgets.index(current)
    else:
        i = -1 if forward else 0
    target = widgets[(i + 1) % len(widgets)] if forward else widgets[(i - 1) % len(widgets)]
    target.setFocus(Qt.FocusReason.TabFocusReason if forward else Qt.FocusReason.BacktabFocusReason)
    return True


def focus_first(container):
    """Give focus to the first reachable widget inside container. Return True if one was found."""
    widgets = focus_chain(container)
    if widgets:
        widgets[0].setFocus(Qt.FocusReason.TabFocusReason)
        return True
    return False
