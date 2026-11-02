# SPDX-License-Identifier: GPL-3.0-only
"""Encabezado de ventana personalizado para entornos Wayland (Sway)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout

class WindowHeader(QWidget):
    def __init__(self, title: str, window: QWidget):
        super().__init__()
        self.target = window

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 8, 8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("headerTitle")
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("headerClose")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setToolTip("Cerrar")
        self.close_btn.clicked.connect(window.close)
        layout.addWidget(self.close_btn)

        self.setFixedHeight(46)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

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
