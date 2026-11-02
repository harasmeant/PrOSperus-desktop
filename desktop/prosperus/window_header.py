# SPDX-License-Identifier: GPL-3.0-only
"""Encabezado de ventana personalizado para entornos Wayland (Sway)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from .branches import flourish
from .window_controls import HoverControls

class WindowHeader(QWidget):
    def __init__(self, title: str, window: QWidget):
        super().__init__()
        # Objeto destino que referencia la ventana principal
        self.target = window

        # Layout horizontal para alinear título y botón de cierre
        layout = QHBoxLayout(self)
        # Espaciado respecto a los bordes de la ventana
        layout.setContentsMargins(18, 10, 10, 20)

        # Etiqueta mostrando el título de la ventana
        self.title_label = QLabel(title)
        # Nombre de objeto para estilizar la etiqueta
        self.title_label.setObjectName("headerTitle")
        layout.addWidget(self.title_label)
        # Espacio derecho de desplazamiento para el botón
        layout.addStretch()

        # Puntos de ventana (ampliar y cerrar) que crecen al pasar el ratón por la ventana.
        # Sin minimizar: Sway no lo implementa y estas ventanas pertenecen al escritorio.
        self.controls = HoverControls(self, watch=window, actions=('maximize', 'close'))
        self.controls.triggered.connect(self.trigger)
        layout.addWidget(self.controls)

        # Altura fija para evitar cambios de layout
        self.setFixedHeight(64)
        # Cursor de mano para indicar que es arrastrable
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # Estilo visual personalizado por nombre de objeto
        self.setStyleSheet("""
            QWidget { background: transparent; }
            QLabel#headerTitle { font-weight: 600; font-size: 17px; letter-spacing: .3px; }
        """)

    def paintEvent(self, event):
        # Remate floral bajo el título (tema de las ventanas de PrOSperus).
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.palette().color(QPalette.ColorRole.WindowText); color.setAlphaF(.3)
        flourish(painter, 18, self.width() - 18, self.height() - 10, color, len(self.title_label.text()))

    def mousePressEvent(self, event):
        # Wayland requiere startSystemMove para mover ventanas
        if event.button() == Qt.MouseButton.LeftButton:
            self.target.windowHandle().startSystemMove()
            event.accept()

    def sway_window(self):
        """(nodo, espacio) de esta ventana en Sway, por proceso y título; None fuera de Sway."""
        if not os.environ.get('SWAYSOCK'):
            return None
        from .window_session import request, walk
        for ws in walk(request(4)):
            if ws.get('type') != 'workspace':
                continue
            for n in walk(ws):
                if n.get('pid') == os.getpid() and n.get('name') == self.target.windowTitle():
                    return n, ws
        return None

    def toggle_maximized(self):
        # Sway no atiende la petición de maximizar de las aplicaciones (showMaximized no hace
        # nada): se amplía por IPC, igual que la píldora de controles, y se vuelve al tamaño guardado.
        try:
            found = self.sway_window()
            if found:
                from .window_handle import maximize_commands
                from .window_session import request
                self.saved = getattr(self, 'saved', {})
                request(0, maximize_commands(*found, self.saved))
                self.controls.set_maximized(found[0]['id'] in self.saved)
                return
        except (OSError, ValueError):
            pass
        # En Wayland el cambio llega después: se marca el estado pedido, no el actual.
        maximized = not self.target.isMaximized()
        self.target.showMaximized() if maximized else self.target.showNormal()
        self.controls.set_maximized(maximized)

    def trigger(self, action):
        self.target.close() if action == 'close' else self.toggle_maximized()

    def mouseDoubleClickEvent(self, event):
        # Alternar maximizado al doble clic
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized()
            event.accept()
