# SPDX-License-Identifier: GPL-3.0-only
"""Encabezado de ventana personalizado para entornos Wayland (Sway)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from .window_controls import HoverControls

class WindowHeader(QWidget):
    def __init__(self, title: str, window: QWidget):
        super().__init__()
        # Objeto destino que referencia la ventana principal
        self.target = window

        # Layout horizontal para alinear título y botón de cierre
        layout = QHBoxLayout(self)
        # Espaciado respecto a los bordes de la ventana
        layout.setContentsMargins(14, 8, 8, 8)

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
        self.setFixedHeight(46)
        # Cursor de mano para indicar que es arrastrable
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # Estilo visual personalizado por nombre de objeto
        self.setStyleSheet("""
            QWidget { background: transparent; }
            QLabel#headerTitle { font-weight: bold; font-size: 16px; }
        """)

    def mousePressEvent(self, event):
        # Wayland requiere startSystemMove para mover ventanas
        if event.button() == Qt.MouseButton.LeftButton:
            self.target.windowHandle().startSystemMove()
            event.accept()

    def toggle_maximized(self):
        self.target.showNormal() if self.target.isMaximized() else self.target.showMaximized()

    def trigger(self, action):
        self.target.close() if action == 'close' else self.toggle_maximized()

    def mouseDoubleClickEvent(self, event):
        # Alternar maximizado al doble clic
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized()
            event.accept()
