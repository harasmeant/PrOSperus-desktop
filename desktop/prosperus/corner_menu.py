# SPDX-License-Identifier: GPL-3.0-only
"""Botón que despliega un menú al pasar el ratón."""
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QPushButton

# Menú que se cierra automáticamente si el ratón no está sobre él o su propietario
class HoverMenu(QMenu):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        # Temporizador para cerrar el menú después de un retraso
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._close_if_no_mouse)

    # Detiene el temporizador al entrar con el ratón
    def enterEvent(self, event):
        self.timer.stop()
        super().enterEvent(event)

    # Inicia el temporizador al salir con el ratón
    def leaveEvent(self, event):
        self.timer.start(300)
        super().leaveEvent(event)

    # Cierra el menú si el ratón no está sobre él o su propietario
    def _close_if_no_mouse(self):
        if not (self.underMouse() or (self.owner and self.owner.underMouse())):
            self.close()

# Botón que abre un menú al hacer clic o al pasar el ratón
class HoverMenuButton(QPushButton):
    def __init__(self, text, icon, actions, parent=None):
        super().__init__(text, parent)
        self.setFlat(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName(text)
        if icon:
            self.setIcon(icon)
        # Menú flotante con temporizador de cierre automático
        self.menu = HoverMenu(self)
        for item in actions:
            if item is None:
                self.menu.addSeparator()
            else:
                label, ic, cb = item
                act = QAction(label, self)
                if ic:
                    act.setIcon(ic)
                # Evita problemas de referencia en los callbacks
                act.triggered.connect(lambda checked=False, cb=cb: cb())
                self.menu.addAction(act)
        self.clicked.connect(self._open_menu)

    # Abre el menú en la posición correcta debajo del botón
    def _open_menu(self):
        if not self.menu.isVisible():
            self.menu.popup(self.mapToGlobal(QPoint(0, self.height())))

    # Abre el menú al pasar el ratón por el botón
    def enterEvent(self, event):
        self._open_menu()
        super().enterEvent(event)

    # Reinicia el temporizador del menú al salir del botón
    def leaveEvent(self, event):
        if self.menu.isVisible():
            self.menu.timer.start(300)
        super().leaveEvent(event)
