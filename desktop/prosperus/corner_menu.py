# SPDX-License-Identifier: GPL-3.0-only
"""Botón que despliega un menú al pasar el ratón."""
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QPushButton

class HoverMenu(QMenu):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._close_if_no_mouse)

    def enterEvent(self, event):
        self.timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.timer.start(300)
        super().leaveEvent(event)

    def _close_if_no_mouse(self):
        if not (self.underMouse() or (self.owner and self.owner.underMouse())):
            self.close()

class HoverMenuButton(QPushButton):
    def __init__(self, text, icon, actions, parent=None):
        super().__init__(text, parent)
        self.setFlat(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(text)
        if icon:
            self.setIcon(icon)
        self.menu = HoverMenu(self)
        for item in actions:
            if item is None:
                self.menu.addSeparator()
            else:
                label, ic, cb = item
                act = QAction(label, self)
                if ic:
                    act.setIcon(ic)
                act.triggered.connect(lambda checked=False, cb=cb: cb())
                self.menu.addAction(act)
        self.clicked.connect(self._open_menu)

    def _open_menu(self):
        if not self.menu.isVisible():
            self.menu.popup(self.mapToGlobal(QPoint(0, self.height())))

    def enterEvent(self, event):
        self._open_menu()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.menu.isVisible():
            self.menu.timer.start(300)
        super().leaveEvent(event)
