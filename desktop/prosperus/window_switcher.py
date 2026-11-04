# SPDX-License-Identifier: GPL-3.0-only
"""Alt+Tab: ventanas abiertas del proyecto, minimizadas incluidas."""
from PySide6.QtCore import Qt, Signal, QRectF, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class SwitcherTile(QPushButton):
    """One window in the Alt+Tab switcher. item is a dict with keys 'name' (str) and 'hidden' (bool)."""
    def __init__(self, item, colors, parent=None):
        super().__init__(parent)
        self.item = item
        self.colors = colors
        self.current = False
        self.setFixedSize(170, 110)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(item['name'] + (' (minimizada)' if item['hidden'] else ''))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.item['hidden']:
            p.setOpacity(0.5)  # minimizada: apagada a la mitad, sin texto que lo diga
        p.setBrush(QColor(self.colors.hover if self.current else self.colors.card))
        p.setPen(QPen(QColor(self.colors.accent if self.current else self.colors.border), 3 if self.current else 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 12, 12)
        font = QFont('DejaVu Sans', 10, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QColor(self.colors.text))
        name = p.fontMetrics().elidedText(self.item['name'], Qt.TextElideMode.ElideRight, self.width() - 20)
        p.drawText(QRectF(10, 14, self.width()-20, self.height()-44), Qt.AlignmentFlag.AlignCenter, name)


class WindowSwitcher(QDialog):
    """Alt+Tab: shows the open windows (minimized included) and picks one when Alt is released."""
    chosen = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Cambiar de ventana')
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.items = []
        self.tiles = []
        self.index = 0
        self.colors = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        self.row = QHBoxLayout()
        self.row.setSpacing(10)
        layout.addLayout(self.row)
        self.caption = QLabel('')
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.caption)

    def step(self, items, direction, colors):
        if not items:
            return
        if not self.isVisible():
            self.colors = colors
            self.items = list(items)
            self.build()
            self.index = (1 if len(items) > 1 else 0) if direction > 0 else len(items) - 1
            self.update_selection()
            self.show()
            self.raise_()
            self.activateWindow()
            self.setFocus()
            # Alt+Tab rápido: si Alt ya se soltó antes de que llegara el foco, no habrá suelta que ver.
            QTimer.singleShot(250, self.check_alt)
            return
        self.index = (self.index + direction) % len(self.items)
        self.update_selection()

    def build(self):
        for tile in self.tiles:
            tile.hide(); tile.deleteLater()
        self.tiles = []
        for i, item in enumerate(self.items):
            tile = SwitcherTile(item, self.colors, self)
            tile.clicked.connect(lambda checked=False, i=i: self.pick(i))
            self.row.addWidget(tile)
            self.tiles.append(tile)
        self.adjustSize()

    def update_selection(self):
        for i, tile in enumerate(self.tiles):
            tile.current = (i == self.index)
            tile.update()
        item = self.items[self.index]
        self.caption.setText(item['name'])

    def check_alt(self):
        if self.isVisible() and not QGuiApplication.queryKeyboardModifiers() & Qt.KeyboardModifier.AltModifier:
            self.pick(self.index)

    def pick(self, index):
        if 0 <= index < len(self.items):
            item = self.items[index]
            self.hide()
            self.chosen.emit(item)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Tab or key == Qt.Key.Key_Right:
            self.step(self.items, 1, self.colors)
        elif key == Qt.Key.Key_Backtab or key == Qt.Key.Key_Left:
            self.step(self.items, -1, self.colors)
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.pick(self.index)
        elif key == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event); return
        event.accept()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Alt and self.isVisible():
            self.pick(self.index)
            return
        super().keyReleaseEvent(event)
