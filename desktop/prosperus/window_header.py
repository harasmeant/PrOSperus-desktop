# SPDX-License-Identifier: GPL-3.0-only
"""Encabezado de ventana personalizado para entornos Wayland (Sway)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout

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

        # Botón de cierre con símbolo universal
        self.close_btn = QPushButton("✕")
        # Nombre de objeto para estilizar el botón
        self.close_btn.setObjectName("headerClose")
        # Tamaño fijo del botón
        self.close_btn.setFixedSize(30, 30)
        # Asistente textual para el botón
        self.close_btn.setToolTip("Cerrar")
        # Conexión de acción al cierre de la ventana destino
        self.close_btn.clicked.connect(window.close)
        layout.addWidget(self.close_btn)

        # Altura fija para evitar cambios de layout
        self.setFixedHeight(46)
        # Cursor de mano para indicar que es arrastrable
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # Estilo visual personalizado por nombre de objeto
        self.setStyleSheet("""
            QWidget { background: transparent; }
            QLabel#headerTitle { font-weight: bold; font-size: 16px; }
            QPushButton#headerClose {
                border: none;
                border-radius: 15px;
                font-size: 15px;
            }
            QPushButton#headerClose:hover { background: rgba(255, 255, 255, 0.12); }
        """)

    def mousePressEvent(self, event):
        # Wayland requiere startSystemMove para mover ventanas
        if event.button() == Qt.MouseButton.LeftButton:
            self.target.windowHandle().startSystemMove()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        # Alternar maximizado al doble clic
        if event.button() == Qt.MouseButton.LeftButton:
            if self.target.isMaximized():
                self.target.showNormal()
            else:
                self.target.showMaximized()
            event.accept()
