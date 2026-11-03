"""Tarjetero de proyectos: portadas apiladas (por defecto) o escritorios en cuadrícula."""
# SPDX-License-Identifier: GPL-3.0-only
from PySide6.QtCore import QEvent, QPoint, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import motion
from .appearance import draw_symbol, paint_wallpaper, palette_for, symbol_icon, wallpaper_for

MIN_CARD = 200  # ancho mínimo de cada tarjeta de la cuadrícula
GRID_KEYS = (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Home,
             Qt.Key.Key_End, Qt.Key.Key_Return, Qt.Key.Key_Enter)
VIEW_KEY = 'projects/view'  # 'stack' (tarjetero) o 'grid' (cuadrícula)
PANEL_WIDTH = {'stack': 370, 'grid': 660}

class Cover(QPushButton):
    def __init__(self, stack, path, offset):
        super().__init__(stack)
        self.stack, self.path, self.offset = stack, path, offset
        shell = stack.drawer.shell
        self.colors = shell.accessibility.palette(palette_for(shell.vault, path))
        self.wallpaper = None if shell.accessibility.high_contrast else wallpaper_for(shell.vault, path)
        self.active = shell.folder.is_relative_to(path)
        self.notes = len(list(shell.vault.notes(path)))
        self.folders = sum(p.is_dir() for p in shell.vault.entries(path))
        self.setAccessibleName(path.name + (' · Abrir proyecto' if offset == 0 else ' · Ver portada'))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: stack.drawer.open_current() if offset == 0 else stack.drawer.step(offset))

    def wheelEvent(self, event):
        self.stack.wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Home, Qt.Key.Key_End):
            self.stack.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        font_size = self.stack.drawer.shell.accessibility.font_size
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath(); clip.addRoundedRect(rect, 12, 12)
        p.setClipPath(clip)
        paint_wallpaper(p, rect, self.wallpaper, self.colors.base, 35 if self.offset == 0 else 125)
        p.setPen(QPen(QColor(self.colors.accent if self.offset == 0 or self.hasFocus() else self.colors.border), 3 if self.hasFocus() else 1.5))
        p.drawRoundedRect(rect, 12, 12)
        p.setPen(QColor(self.colors.text))
        if self.offset:
            p.setFont(QFont('DejaVu Sans', font_size(10), QFont.Weight.Bold))
            y = 10 if self.offset < 0 else self.height() - 35
            p.drawText(QRectF(16, y, self.width() - 32, 25), Qt.AlignmentFlag.AlignVCenter, self.path.name)
            return
        draw_symbol(p, QRectF(20, 20, 24, 24), 'folder', self.colors.accent)
        p.setFont(QFont('DejaVu Sans', font_size(8), QFont.Weight.Bold))
        p.drawText(QRectF(54, 20, 130, 24), Qt.AlignmentFlag.AlignVCenter, 'P R O Y E C T O')
        if self.active:
            p.setPen(QColor(self.colors.accent))
            p.drawText(QRectF(self.width() - 84, 20, 65, 24), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 'En uso')
        p.setPen(QColor(self.colors.text))
        p.setFont(QFont('DejaVu Sans', font_size(21), QFont.Weight.Bold))
        p.drawText(QRectF(20, self.height() - 125, self.width() - 40, 85), Qt.AlignmentFlag.AlignBottom | Qt.TextFlag.TextWordWrap, self.path.name)
        p.setFont(QFont('DejaVu Sans', font_size(9)))
        p.setPen(QColor(self.colors.muted))
        p.drawText(QRectF(20, self.height() - 34, self.width() - 105, 22), Qt.AlignmentFlag.AlignVCenter, f'{self.notes} notas · {self.folders} carpetas')
        p.setPen(QColor(self.colors.accent))
        p.drawText(QRectF(self.width() - 88, self.height() - 34, 68, 22), Qt.AlignmentFlag.AlignCenter, 'Abrir ↗')


class CoverStack(QWidget):
    def __init__(self, drawer):
        super().__init__(drawer)
        self.drawer = drawer
        self.cards = []
        self.setMinimumHeight(250)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Tarjetero de proyectos; usa las flechas arriba y abajo')

    def rebuild(self):
        # Crear primero las portadas del fondo y la activa al final conserva
        # el orden de apilado visual cuando arrange() las eleva con raise_().
        for card in self.cards:
            card.hide(); card.deleteLater()
        self.cards = []
        count = len(self.drawer.filtered)
        offsets = [-2, 2, -1, 1, 0] if count >= 5 else ([-1, 2, 1, 0] if count == 4 else ([-1, 1, 0] if count == 3 else ([1, 0] if count == 2 else ([0] if count else []))))
        for offset in offsets:
            path = self.drawer.filtered[(self.drawer.index + offset) % count]
            card = Cover(self, path, offset)
            self.cards.append(card)
            card.show()
        self.arrange()

    def arrange(self):
        height = min(410, max(180, self.height() - 128))
        top = (self.height() - height) // 2
        for card in self.cards:
            inset = 8 + abs(card.offset) * 12
            card.setGeometry(inset, top + card.offset * 43, max(80, self.width() - inset * 2), height)
            card.raise_()

    def resizeEvent(self, event):
        self.arrange()

    def wheelEvent(self, event):
        if event.angleDelta().y():
            self.drawer.step(-1 if event.angleDelta().y() > 0 else 1)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.drawer.step(-1 if event.key() == Qt.Key.Key_Up else 1)
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.drawer.open_current()
        elif event.key() in (Qt.Key.Key_Home, Qt.Key.Key_End):
            self.drawer.index = 0 if event.key() == Qt.Key.Key_Home else max(0, len(self.drawer.filtered) - 1)
            self.drawer.refresh()
        else:
            super().keyPressEvent(event)


class GridCard(QPushButton):
    """Tarjeta de un escritorio: su fondo, nombre y contenido."""
    HEIGHT = 150

    def __init__(self, grid, path, position):
        super().__init__()
        self.grid, self.path, self.position = grid, path, position
        self.hover = False
        # Resaltado al pasar el ratón con fundido (0 normal → 1 encima).
        self.glow = 0.0
        self.glow_animation = QVariantAnimation(self, duration=160)
        self.glow_animation.valueChanged.connect(self._set_glow)
        shell = grid.drawer.shell
        self.colors = shell.accessibility.palette(palette_for(shell.vault, path))
        self.wallpaper = None if shell.accessibility.high_contrast else wallpaper_for(shell.vault, path)
        self.active = shell.folder.is_relative_to(path)
        self.notes = len(list(shell.vault.notes(path)))
        self.folders = sum(p.is_dir() for p in shell.vault.entries(path))
        self.setAccessibleName(path.name + ' · Abrir escritorio')
        self.setToolTip(path.name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(MIN_CARD)
        self.height_ = round(self.HEIGHT * shell.accessibility.text_scale / 100)
        self.setFixedHeight(self.height_)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clicked.connect(self.open)

    def event(self, event):
        # Las hojas de estilo (min-height de los botones) fijan el mínimo al aplicarse: se recupera el alto.
        result = super().event(event)
        if event.type() in (QEvent.Type.Polish, QEvent.Type.StyleChange) and self.minimumHeight() != self.height_:
            self.setFixedHeight(self.height_)
        return result

    def open(self):
        self.grid.drawer.move_to(self.position)
        self.grid.drawer.open_current()

    def selected(self):
        return self.position == self.grid.drawer.index

    def _set_glow(self, value):
        self.glow = value; self.update()

    def _fade_hover(self, on):
        self.hover = on
        self.glow_animation.stop()
        self.glow_animation.setStartValue(self.glow); self.glow_animation.setEndValue(1.0 if on else 0.0)
        self.glow_animation.start()

    def enterEvent(self, event):
        self._fade_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._fade_hover(False)
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() in GRID_KEYS:
            self.grid.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        font_size = self.grid.drawer.shell.accessibility.font_size
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        clip = QPainterPath(); clip.addRoundedRect(rect, 12, 12)
        p.save(); p.setClipPath(clip)
        paint_wallpaper(p, rect, self.wallpaper, self.colors.base, round(70 - 30 * self.glow))
        # Degradado inferior para que el nombre se lea sobre cualquier fondo.
        shade = QLinearGradient(0, rect.bottom() - 70, 0, rect.bottom())
        shade.setColorAt(0, QColor(0, 0, 0, 0)); shade.setColorAt(1, QColor(0, 0, 0, 120))
        p.fillRect(rect, shade)
        p.restore()
        strong = self.selected() or self.hasFocus()
        p.setPen(QPen(QColor(self.colors.accent if strong or self.hover else self.colors.border), 3 if strong else 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 12, 12)
        draw_symbol(p, QRectF(14, 14, 20, 20), 'folder', self.colors.accent)
        if self.active:
            p.setFont(QFont('DejaVu Sans', font_size(8), QFont.Weight.Bold))
            badge = QRectF(self.width() - 76, 13, 62, 22)
            fill = QColor(self.colors.panel); fill.setAlpha(200)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(fill); p.drawRoundedRect(badge, 11, 11)
            p.setPen(QColor(self.colors.accent))
            p.drawText(badge, Qt.AlignmentFlag.AlignCenter, 'En uso')
        p.setPen(QColor(self.colors.text))
        p.setFont(QFont('DejaVu Sans', font_size(13), QFont.Weight.Bold))
        p.drawText(QRectF(14, 40, self.width() - 28, self.height() - 72),
                   Qt.AlignmentFlag.AlignBottom | Qt.TextFlag.TextWordWrap, self.path.name)
        p.setFont(QFont('DejaVu Sans', font_size(8)))
        p.setPen(QColor(self.colors.muted))
        p.drawText(QRectF(14, self.height() - 30, self.width() - 28, 20), Qt.AlignmentFlag.AlignVCenter,
                   f'{self.notes} notas · {self.folders} carpetas')


class ProjectGrid(QScrollArea):
    """Escritorios en cuadrícula: flechas en las cuatro direcciones, Intro abre."""
    SPACING = 12

    def __init__(self, drawer):
        super().__init__(drawer)
        self.drawer = drawer
        self.cards = []
        self.columns = 1
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet('QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }')
        self.viewport().setAutoFillBackground(False)
        self.content = QWidget()
        self.layout_ = QGridLayout(self.content)
        self.layout_.setSpacing(self.SPACING); self.layout_.setContentsMargins(2, 2, 2, 2)
        self.setWidget(self.content)
        self.setMinimumHeight(170)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Cuadrícula de escritorios; usa las flechas')

    def fit_columns(self):
        return max(1, (self.viewport().width() + self.SPACING) // (MIN_CARD + self.SPACING))

    def rebuild(self):
        for card in self.cards:
            self.layout_.removeWidget(card); card.hide(); card.deleteLater()
        self.cards = [GridCard(self, path, i) for i, path in enumerate(self.drawer.filtered)]
        self.place()
        self.ensure_current_visible()

    def place(self):
        self.columns = self.fit_columns()
        for row in range(self.layout_.rowCount()):
            self.layout_.setRowStretch(row, 0)
        for card in self.cards:
            self.layout_.removeWidget(card)
        for i, card in enumerate(self.cards):
            self.layout_.addWidget(card, i // self.columns, i % self.columns)
            card.show()
        for column in range(self.layout_.columnCount()):
            self.layout_.setColumnStretch(column, 1 if column < self.columns else 0)
        self.layout_.setRowStretch(-(-len(self.cards) // self.columns), 1)

    def ensure_current_visible(self):
        if 0 <= self.drawer.index < len(self.cards):
            self.ensureWidgetVisible(self.cards[self.drawer.index], 0, 12)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_columns() != self.columns:
            self.place()

    def keyPressEvent(self, event):
        key, count = event.key(), len(self.drawer.filtered)
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.drawer.step(-1 if key == Qt.Key.Key_Left else 1)
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.drawer.move_to(self.drawer.index + (-self.columns if key == Qt.Key.Key_Up else self.columns))
            self.setFocus()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.drawer.open_current()
        elif key in (Qt.Key.Key_Home, Qt.Key.Key_End):
            self.drawer.move_to(0 if key == Qt.Key.Key_Home else count - 1)
        else:
            super().keyPressEvent(event)


class ProjectDrawer(QFrame):
    def __init__(self, shell):
        super().__init__(shell.background)
        self.shell = shell
        self.index = 0
        self.pinned = False
        self.filtered = []
        self.setObjectName('sidebar')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 24, 18, 16)
        row = QHBoxLayout()
        title = QLabel('Tus proyectos'); title.setObjectName('noteTitle')
        row.addWidget(title, 1)
        self.view = 'grid' if str(shell.settings.value(VIEW_KEY, 'stack')) == 'grid' else 'stack'
        self.view_button = QPushButton(); self.view_button.clicked.connect(self.toggle_view)
        row.addWidget(self.view_button)
        self.pin = QPushButton('Fijar'); self.pin.setCheckable(True)
        self.pin.toggled.connect(self.set_pinned); row.addWidget(self.pin)
        close = QPushButton('×'); close.setAccessibleName('Cerrar tarjetero')
        close.clicked.connect(self.hide); row.addWidget(close)
        layout.addLayout(row)
        self.search = QLineEdit(); self.search.setPlaceholderText('Proyecto o contenido de sus notas…')
        self.search.setToolTip('Busca en nombres y en el texto guardado de las notas Markdown de cada proyecto.')
        self.search.setAccessibleName('Buscar proyectos')
        self.search.textChanged.connect(self.filter_projects)
        layout.addWidget(self.search)
        self.layout_ = layout
        self.stack = self.make_view(); layout.addWidget(self.stack, 1)
        nav = QHBoxLayout()
        self.previous = QPushButton(); self.previous.clicked.connect(lambda: self.step(-1))
        nav.addWidget(self.previous)
        self.position = QLabel(); self.position.setObjectName('muted'); self.position.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.position, 1)
        self.next = QPushButton(); self.next.clicked.connect(lambda: self.step(1)); nav.addWidget(self.next)
        layout.addLayout(nav)
        self.hint = hint = QLabel()
        hint.setObjectName('muted'); hint.setWordWrap(True); hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        root = QPushButton('Todos los proyectos'); root.clicked.connect(self.open_root); layout.addWidget(root)
        actions = QHBoxLayout()
        create = QPushButton('Nuevo proyecto'); create.clicked.connect(shell.new_project); actions.addWidget(create)
        import_project = QPushButton('Importar proyecto…')
        import_project.clicked.connect(lambda: shell.files.import_folder(shell.vault.root)); actions.addWidget(import_project)
        layout.addLayout(actions)
        self.label_view()
        self.hide()

    def make_view(self):
        return ProjectGrid(self) if self.view == 'grid' else CoverStack(self)

    def label_view(self):
        grid = self.view == 'grid'
        # Solo icono (el título no cabe con texto en el tarjetero): el del modo al que se cambia.
        self.view_button.setIcon(symbol_icon('folders' if grid else 'apps', '#d4dbc8'))
        self.view_button.setToolTip('Ver los proyectos como ' + ('tarjetero apilado' if grid else 'cuadrícula'))
        self.view_button.setAccessibleName(self.view_button.toolTip())
        self.previous.setText('‹ Anterior' if grid else '↑ Anterior')
        self.next.setText('Siguiente ›' if grid else 'Siguiente ↓')
        self.hint.setText('Flechas para moverte · Intro o clic para abrir' if grid
                          else 'Rueda o ↑ ↓ para explorar · Pulsa la portada para abrir')

    def panel_width(self):
        return PANEL_WIDTH[self.view]

    def set_view(self, view):
        """Cambia entre tarjetero ('stack') y cuadrícula ('grid') y lo recuerda."""
        if view not in PANEL_WIDTH or view == self.view:
            return
        self.view = view
        self.shell.settings.setValue(VIEW_KEY, view)
        old = self.stack
        self.stack = self.make_view()
        self.layout_.replaceWidget(old, self.stack)
        old.hide(); old.deleteLater()
        self.label_view()
        self.shell.position_overlays()
        self.refresh()
        self.stack.setFocus()
        motion.fade_in(self.stack.cards[:12], 220, 28)

    def toggle_view(self):
        self.set_view('stack' if self.view == 'grid' else 'grid')

    def set_pinned(self, value):
        self.pinned = value
        self.pin.setText('Fijado' if value else 'Fijar')

    def open_root(self):
        self.shell.navigate(self.shell.vault.root)
        if not self.pinned:
            self.hide()

    def reveal(self):
        self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
        self.filtered = list(self.shell.project_paths)
        self.index = next((i for i, p in enumerate(self.filtered) if self.shell.folder.is_relative_to(p)), 0)
        self.refresh()
        entering = not self.isVisible()
        self.show(); self.raise_(); self.stack.setFocus()
        if entering:
            # Entra desde el borde izquierdo y las portadas aparecen una tras otra.
            motion.slide_in(self, QPoint(-self.width(), 0), 260)
            motion.fade_in(self.stack.cards[:12], 220, 28)

    def hide(self):
        # Sale hacia la izquierda (una imagen del panel): el panel real queda oculto al momento.
        motion.ghost_out(self, QPoint(-self.width(), 0), 190)

    def filter_projects(self):
        try:
            self.filtered = self.shell.vault.search_projects(self.search.text())
        except (OSError, ValueError) as error:
            self.filtered = []
            self.shell.status.setText(str(error))
        self.index = 0
        self.refresh()

    def step(self, direction):
        if self.filtered:
            self.index = (self.index + direction) % len(self.filtered)
            self.update_selection()
            self.stack.setFocus()

    def move_to(self, index):
        """Selecciona sin dar la vuelta (cuadrícula: flechas verticales, Inicio, Fin, clic)."""
        if self.filtered:
            self.index = max(0, min(index, len(self.filtered) - 1))
            self.update_selection()

    def update_selection(self):
        if self.view == 'stack':
            self.refresh(); return  # el tarjetero recoloca las portadas alrededor de la actual
        self.position.setText(f'{self.index + 1} / {len(self.filtered)}' if self.filtered else 'Sin resultados')
        for card in self.stack.cards:
            card.update()
        self.stack.ensure_current_visible()

    def refresh(self):
        self.stack.rebuild()
        self.position.setText(f'{self.index + 1} / {len(self.filtered)}' if self.filtered else 'Sin resultados')
        self.previous.setEnabled(len(self.filtered) > 1); self.next.setEnabled(len(self.filtered) > 1)

    def open_current(self):
        if self.filtered:
            self.shell.navigate(self.filtered[self.index])
            if not self.pinned:
                self.hide()

    def leaveEvent(self, event):
        if not self.pinned:
            self.hide()
        super().leaveEvent(event)


class ProjectEdge(QPushButton):
    def __init__(self, shell):
        super().__init__('›', shell.background)
        self.shell = shell
        self.setAccessibleName('Abrir tarjetero de proyectos')
        self.setToolTip('Carpetas')
        self.clicked.connect(shell.drawer.reveal)

    def enterEvent(self, event):
        self.shell.drawer.reveal()
        super().enterEvent(event)
