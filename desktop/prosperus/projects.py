"""The vertical project cover stack used in the Obsidian reference."""
# SPDX-License-Identifier: GPL-3.0-only
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from .appearance import draw_symbol, paint_wallpaper, palette_for, wallpaper_for


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
        self.stack = CoverStack(self); layout.addWidget(self.stack, 1)
        nav = QHBoxLayout()
        self.previous = QPushButton('↑ Anterior'); self.previous.clicked.connect(lambda: self.step(-1))
        nav.addWidget(self.previous)
        self.position = QLabel(); self.position.setObjectName('muted'); self.position.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.position, 1)
        self.next = QPushButton('Siguiente ↓'); self.next.clicked.connect(lambda: self.step(1)); nav.addWidget(self.next)
        layout.addLayout(nav)
        hint = QLabel('Rueda o ↑ ↓ para explorar · Pulsa la portada para abrir')
        hint.setObjectName('muted'); hint.setWordWrap(True); hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        root = QPushButton('Todos los proyectos'); root.clicked.connect(self.open_root); layout.addWidget(root)
        actions = QHBoxLayout()
        create = QPushButton('Nuevo proyecto'); create.clicked.connect(shell.new_project); actions.addWidget(create)
        import_project = QPushButton('Importar proyecto…')
        import_project.clicked.connect(lambda: shell.files.import_folder(shell.vault.root)); actions.addWidget(import_project)
        layout.addLayout(actions)
        self.hide()

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
        self.show(); self.raise_(); self.stack.setFocus()

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
            self.refresh()
            self.stack.setFocus()

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
