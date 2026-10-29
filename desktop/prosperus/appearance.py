"""Project colours and inherited wallpapers from the accepted Obsidian demo."""
# SPDX-License-Identifier: GPL-3.0-only
from functools import lru_cache
import hashlib

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget


HUES = {'Bienvenida': 92, 'Cuaderno': 34, 'Laboratorio': 207,
        'Permacultivo': 92, 'DND': 30, 'Club social': 38,
        'Escritorio Obsidian': 145, 'Cursos 3D': 207, 'Máster Tienda': 345}


class Palette:
    def __init__(self, hue=145):
        def colour(saturation, lightness):
            return QColor.fromHsl(hue, saturation, lightness).name()
        self.base = colour(45, 19)
        self.panel = colour(48, 32)
        self.card = colour(48, 43)
        self.hover = colour(49, 57)
        self.border = colour(40, 82)
        self.accent = colour(65, 177)
        self.text = colour(28, 224)
        self.muted = colour(25, 158)

    def css(self):
        return f"""
        QWidget {{ background: transparent; color: {self.text}; font-family: 'DejaVu Sans'; font-size: 13px; }}
        QMainWindow, QDialog {{ background: {self.base}; }}
        QPushButton {{ background: {self.card}; border: 1px solid {self.border}; border-radius: 8px; padding: 9px 13px; text-align: left; }}
        QPushButton:hover {{ background: {self.hover}; border-color: {self.accent}; }}
        QPushButton:focus {{ border: 2px solid {self.accent}; }}
        QPushButton:disabled {{ color: {self.muted}; border-color: {self.panel}; }}
        QPushButton#minimized {{ background: {self.hover}; border: 2px solid {self.accent}; }}
        QLineEdit {{ background: {self.panel}; border: 1px solid {self.border}; border-radius: 8px; padding: 9px; selection-background-color: {self.hover}; }}
        QLabel#title {{ font-size: 30px; font-weight: bold; }}
        QLabel#eyebrow {{ color: {self.accent}; font-size: 11px; letter-spacing: 2px; }}
        QLabel#muted {{ color: {self.muted}; font-size: 11px; }}
        QFrame#sidebar {{ background: {self.base}; border-right: 1px solid {self.border}; }}
        QFrame#dock {{ background: {self.panel}; border: 1px solid {self.border}; border-radius: 14px; }}
        QFrame#note {{ border: 1px solid {self.accent}; border-radius: 12px; }}
        QLabel#noteTitle {{ font-size: 14px; font-weight: bold; }}
        QTextBrowser, QPlainTextEdit {{ border: none; background: transparent; padding: 15px; selection-background-color: {self.hover}; font-size: 15px; }}
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:horizontal {{ height: 6px; background: transparent; }}
        QScrollBar:vertical {{ width: 7px; background: transparent; }}
        QScrollBar::handle {{ background: {self.border}; border-radius: 3px; min-width: 24px; min-height: 24px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        QToolTip {{ background: {self.panel}; color: {self.text}; border: 1px solid {self.border}; }}
        """


def palette_for(vault, folder):
    folder = vault.checked(folder)
    relative = folder.relative_to(vault.root)
    name = relative.parts[0] if relative.parts else ''
    hue = HUES.get(name, int(hashlib.sha256(name.encode()).hexdigest()[:4], 16) % 360 if name else 145)
    return Palette(hue)


def wallpaper_for(vault, folder):
    current = vault.checked(folder)
    if current.is_file():
        current = current.parent
    while True:
        for suffix in ('png', 'jpg', 'jpeg', 'webp', 'avif'):
            candidate = current / ('wallpaper.' + suffix)
            if candidate.is_file():
                try:
                    return vault.checked(candidate)
                except (OSError, ValueError):
                    continue
        if current == vault.root:
            return None
        current = current.parent


@lru_cache(maxsize=12)
def wallpaper_pixmap(path, modified):
    return QPixmap(str(path))


def paint_wallpaper(painter, rect, path, base, shade=80):
    painter.fillRect(rect, QColor(base))
    if path:
        try:
            pixmap = wallpaper_pixmap(path, path.stat().st_mtime_ns)
        except OSError:
            pixmap = QPixmap()
        if not pixmap.isNull():
            scale = max(rect.width() / pixmap.width(), rect.height() / pixmap.height())
            w, h = rect.width() / scale, rect.height() / scale
            source = QRectF((pixmap.width() - w) / 2, (pixmap.height() - h) / 2, w, h)
            painter.drawPixmap(QRectF(rect), pixmap, source)
    painter.fillRect(rect, QColor(0, 0, 0, shade))


def draw_symbol(painter, rect, kind, color):
    painter.save()
    painter.translate(rect.x(), rect.y())
    painter.scale(rect.width() / 24, rect.height() / 24)
    painter.setPen(QPen(QColor(color), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    if kind == 'folder':
        path.moveTo(3, 7); path.lineTo(3, 4); path.lineTo(10, 4); path.lineTo(13, 7); path.lineTo(21, 7)
        path.lineTo(21, 19); path.lineTo(3, 19); path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(4, 10, 17, 10)
    elif kind == 'window':
        painter.drawRoundedRect(QRectF(3, 4, 18, 16), 2, 2)
        painter.drawLine(3, 9, 21, 9)
    else:
        path.moveTo(6, 3); path.lineTo(14, 3); path.lineTo(19, 8); path.lineTo(19, 21)
        path.lineTo(6, 21); path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(14, 3, 14, 8); painter.drawLine(14, 8, 19, 8)
        painter.drawLine(9, 12, 16, 12); painter.drawLine(9, 16, 16, 16)
    painter.restore()


def symbol_icon(kind, color):
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_symbol(painter, QRectF(0, 0, 24, 24), kind, color)
    painter.end()
    return QIcon(pixmap)


class Wallpaper(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wallpaper = None
        self.palette = Palette()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        paint_wallpaper(painter, self.rect(), self.wallpaper, self.palette.base, 60)
