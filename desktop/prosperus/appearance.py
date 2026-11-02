"""Project colours and inherited wallpapers from the accepted Obsidian demo."""
# SPDX-License-Identifier: GPL-3.0-only
from functools import lru_cache
import hashlib
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget


# Predefinidos para projects con nombre concreto; el resto se calculan por hash
HUES = {'Bienvenida': 92, 'Cuaderno': 34, 'Laboratorio': 207,
        'Permacultivo': 92, 'DND': 30, 'Club social': 38,
        'Escritorio Obsidian': 145, 'Cursos 3D': 207, 'Máster Tienda': 345}


# Genera una paleta de colores a partir de un tono base (HSL)
class Palette:
    def __init__(self, hue=145):
        # Convierte HSL a hex para cada rol de color
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
        # Velo del prototipo: --pd-shade = hsl(h, s, 5%), teñido, no negro.
        self.shade = colour(45, 13)

    # Devuelve hoja de estilos CSS lista para aplicar
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


# Devuelve la Palette adecuada: si hay wallpaper, usa su tono; si no, usa HUES o hash del nombre
def palette_for(vault, folder):
    folder = vault.checked(folder)
    wallpaper = wallpaper_for(vault, folder)
    if wallpaper:
        try:
            modified = wallpaper.stat().st_mtime_ns
        except OSError:
            modified = None
        hue = wallpaper_hue(wallpaper, modified)
        if hue is not None:
            return Palette(hue)
    relative = folder.relative_to(vault.root)
    name = relative.parts[0] if relative.parts else ''
    hue = HUES.get(name, int(hashlib.sha256(name.encode()).hexdigest()[:4], 16) % 360 if name else 145)
    return Palette(hue)


# Busca recursivamente un archivo wallpaper.{png,jpg,...} en folder o sus padres, hasta vault.root
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


# Cachea Pixmaps para evitar recargas; modificado permite invalidar cuando cambia el archivo
@lru_cache(maxsize=12)
def wallpaper_pixmap(path, modified):
    return QPixmap(str(path))


# Calcula el tono circular promedio del wallpaper, ponderado por saturación y valor; cacheado
@lru_cache(maxsize=32)
def wallpaper_hue(path, modified):
    """Devuelve el tono circular promedio del wallpaper."""
    image = QImage(str(path))
    if image.isNull():
        return None
    image = image.scaled(48, 48, Qt.IgnoreAspectRatio, Qt.FastTransformation)
    total_weight = 0.0
    weighted_x = 0.0
    weighted_y = 0.0
    for y in range(image.height()):
        for x in range(image.width()):
            color = QColor(image.pixel(x, y))
            hue = color.hue()
            if hue == -1:   # píxel inválido
                continue
            saturation = color.saturation()
            value = color.value()
            weight = saturation * value
            if weight <= 0:
                continue
            rad = math.radians(hue)
            weighted_x += weight * math.cos(rad)
            weighted_y += weight * math.sin(rad)
            total_weight += weight
    if total_weight < 1:
        return None
    hue_deg = math.degrees(math.atan2(weighted_y, weighted_x))
    if hue_deg < 0:
        hue_deg += 360
    return int(round(hue_deg))


# Pinta el fondo: base color, wallpaper escalado y sombra superpuesta
# shade puede ser un número (velo uniforme) o (arriba, centro, abajo) para un
# degradado vertical: oscurece solo donde hay texto y deja ver la foto.
def paint_wallpaper(painter, rect, path, base, shade=80, tint='#000000'):
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
    if isinstance(shade, tuple):
        top, middle, bottom = shade
        veil = QLinearGradient(0, rect.top(), 0, rect.bottom())
        for stop, alpha in ((0, top), (0.22, middle), (0.70, middle), (1, bottom)):
            colour = QColor(tint); colour.setAlpha(alpha)
            veil.setColorAt(stop, colour)
        painter.fillRect(rect, veil)
    else:
        colour = QColor(tint); colour.setAlpha(shade)
        painter.fillRect(rect, colour)


# Dibuja un símbolo vectorial en el rectángulo dado (coordenadas 0-24)
def draw_symbol(painter, rect, kind, color):
    painter.save()
    painter.translate(rect.x(), rect.y())
    # Escala el path de 24x24 al tamaño real del rectángulo
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
    elif kind == 'folders':
        # Dos carpetas desplazadas
        p1 = QPainterPath()
        p1.moveTo(3, 7); p1.lineTo(3, 4); p1.lineTo(10, 4); p1.lineTo(13, 7); p1.lineTo(21, 7)
        p1.lineTo(21, 19); p1.lineTo(3, 19); p1.closeSubpath()
        painter.drawPath(p1)
        p2 = QPainterPath()
        p2.moveTo(7, 11); p2.lineTo(7, 8); p2.lineTo(14, 8); p2.lineTo(17, 11); p2.lineTo(21, 11)
        p2.lineTo(21, 23); p2.lineTo(7, 23); p2.closeSubpath()
        painter.drawPath(p2)
    elif kind == 'search':
        # Círculo r=6 en (10,10) + mango a (20,20)
        painter.drawEllipse(QPointF(10, 10), 6, 6)
        painter.drawLine(14, 14, 20, 20)
    elif kind == 'note-plus':
        # Nota más pequeña + '+' en esquina inferior derecha
        p = QPainterPath()
        p.moveTo(8, 5); p.lineTo(14, 5); p.lineTo(17, 8); p.lineTo(17, 19)
        p.lineTo(8, 19); p.closeSubpath()
        painter.drawPath(p)
        painter.drawLine(14, 5, 14, 8); painter.drawLine(14, 8, 17, 8)
        # signo +
        painter.drawLine(14, 15, 18, 15)
        painter.drawLine(16, 13, 16, 17)
    elif kind == 'folder-plus':
        # Contorno de carpeta + '+' centrado
        p = QPainterPath()
        p.moveTo(3, 7); p.lineTo(3, 4); p.lineTo(10, 4); p.lineTo(13, 7); p.lineTo(21, 7)
        p.lineTo(21, 19); p.lineTo(3, 19); p.closeSubpath()
        painter.drawPath(p)
        # signo + en centro (12,13)
        painter.drawLine(9, 13, 15, 13)
        painter.drawLine(12, 10, 12, 16)
    elif kind == 'apps':
        # 2x2 cuadrados redondeados 7x7, gap 2, desde (4,4)
        for i in range(2):
            for j in range(2):
                x = 4 + j * 9
                y = 4 + i * 9
                painter.drawRoundedRect(QRectF(x, y, 7, 7), 1, 1)
    elif kind == 'sliders':
        # 3 líneas horizontales con perillas circulares en x distintas
        for i, (y, knob_x) in enumerate([(6, 8), (12, 12), (18, 16)]):
            painter.drawLine(4, y, 20, y)
            painter.drawEllipse(QPointF(knob_x, y), 3, 3)
    elif kind == 'help':
        # Círculo r=9 centrado + '?' (arco y punto)
        painter.drawEllipse(QPointF(12, 12), 9, 9)
        qp = QPainterPath()
        qp.moveTo(12, 7)
        qp.arcTo(QRectF(9, 7, 6, 6), 0, -180)
        qp.lineTo(12, 13)
        qp.lineTo(12, 15)
        painter.drawPath(qp)
        painter.drawEllipse(QPointF(12, 17), 1, 1)
    elif kind == 'refresh':
        # Arco circular abierto ~300° r=7 + flecha
        p = QPainterPath()
        p.arcMoveTo(QRectF(5, 5, 14, 14), 30)
        p.arcTo(QRectF(5, 5, 14, 14), 30, -300)
        painter.drawPath(p)
        painter.drawLine(11, 17, 12, 19)
        painter.drawLine(13, 17, 12, 19)
    elif kind == 'save':
        # Marca de verificación
        painter.drawLine(7, 12, 11, 16)
        painter.drawLine(11, 16, 17, 8)
    elif kind == 'close':
        # X
        painter.drawLine(7, 7, 17, 17)
        painter.drawLine(17, 7, 7, 17)
    elif kind == 'power':
        # Arco abierto arriba + línea vertical
        p = QPainterPath()
        p.arcMoveTo(QRectF(5, 5, 14, 14), 45)
        p.arcTo(QRectF(5, 5, 14, 14), 45, 270)
        painter.drawPath(p)
        painter.drawLine(12, 8, 12, 16)
    elif kind == 'restart':
        # Arco circular + flecha, espejo de refresh
        p = QPainterPath()
        p.arcMoveTo(QRectF(5, 5, 14, 14), 150)
        p.arcTo(QRectF(5, 5, 14, 14), 150, 300)
        painter.drawPath(p)
        painter.drawLine(11, 7, 12, 5)
        painter.drawLine(13, 7, 12, 5)
    else:
        path.moveTo(6, 3); path.lineTo(14, 3); path.lineTo(19, 8); path.lineTo(19, 21)
        path.lineTo(6, 21); path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(14, 3, 14, 8); painter.drawLine(14, 8, 19, 8)
        painter.drawLine(9, 12, 16, 12); painter.drawLine(9, 16, 16, 16)
    painter.restore()


# Crea un QIcon de 24x24 renderizando el símbolo con el color dado
def symbol_icon(kind, color):
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_symbol(painter, QRectF(0, 0, 24, 24), kind, color)
    painter.end()
    return QIcon(pixmap)


# QWidget que pinta el fondo de pantalla heredado
class Wallpaper(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wallpaper = None
        self.palette = Palette()

    # paintEvent personalizado: usa paint_wallpaper con la palette base
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        paint_wallpaper(painter, self.rect(), self.wallpaper, self.palette.base, (110, 30, 120), self.palette.shade)
# Iconos minimalistas (referencia estética)
# Referencia: Numix / Papirus / Breeze minimal


# Rasgos del fondo para las ramas procedurales (0..1): rectitud (objetos fabricados),
# detalle (textura) y brillo (destellos). Se recalculan solo si cambia el archivo.
@lru_cache(maxsize=32)
def wallpaper_traits(path, modified):
    image = QImage(str(path))
    if image.isNull():
        return None
    w, h = 160, 100
    image = image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    grey = [[QColor(image.pixel(x, y)).lightness() for x in range(w)] for y in range(h)]
    edges, magnitude_sum, sparks = {}, 0.0, 0
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            gx = (grey[y-1][x+1] + 2 * grey[y][x+1] + grey[y+1][x+1]) - (grey[y-1][x-1] + 2 * grey[y][x-1] + grey[y+1][x-1])
            gy = (grey[y+1][x-1] + 2 * grey[y+1][x] + grey[y+1][x+1]) - (grey[y-1][x-1] + 2 * grey[y-1][x] + grey[y-1][x+1])
            magnitude = math.hypot(gx, gy); magnitude_sum += magnitude
            if magnitude > 140:
                edges[(x, y)] = math.atan2(gy, gx)
            around = (grey[y-1][x] + grey[y+1][x] + grey[y][x-1] + grey[y][x+1]) / 4
            if grey[y][x] > 120 and grey[y][x] - around > 25:
                sparks += 1
    # Borde recto: 5 px antes y después a lo largo del borde siguen con la misma orientación.
    straight = 0
    for (x, y), angle in edges.items():
        along = (-math.sin(angle), math.cos(angle))
        def same(step):
            other = edges.get((round(x + along[0] * step), round(y + along[1] * step)))
            if other is None:
                return False
            d = abs((angle - other + math.pi) % (2 * math.pi) - math.pi)
            return min(d, math.pi - d) < .14
        straight += same(5) and same(-5)
    clamp = lambda v: max(0.0, min(1.0, v))
    inner = (w - 2) * (h - 2)
    return {'straight': clamp((straight / len(edges) if edges else 0) / .22),
            'detail': clamp((magnitude_sum / inner - 12) / 24),
            'glow': clamp(sparks / inner * 40),
            'seed': int(hashlib.sha256(str(path).encode()).hexdigest()[:6], 16)}
