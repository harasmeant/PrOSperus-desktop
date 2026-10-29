"""Project desktop following the accepted Obsidian visual reference."""
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import math
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QPainterPath, QPen, QShortcut, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QInputDialog,
    QLabel, QLayout, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSizeGrip, QStackedWidget,
    QTextBrowser, QVBoxLayout, QWidget)

from . import __version__
from .appearance import (Palette, Wallpaper, draw_symbol, paint_wallpaper,
                         palette_for, symbol_icon, wallpaper_for)
from .model import Vault
from .projects import ProjectDrawer, ProjectEdge
from .launcher import ApplicationBrowser, ApplicationService

STYLE = Palette().css()


def button(text, callback, parent=None):
    widget = QPushButton(text, parent)
    widget.clicked.connect(callback)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    return widget


class SafeReader(QTextBrowser):
    def loadResource(self, kind, url):
        return None


class DragTitle(QLabel):
    def __init__(self, text, panel):
        super().__init__(text, panel)
        self.panel = panel
        self.offset = None
        self.setObjectName('noteTitle')
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event):
        self.panel.raise_()
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.panel.pos()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint() - self.offset
            area = self.panel.parentWidget().rect()
            self.panel.move(max(0, min(pos.x(), area.width() - self.panel.width())),
                            max(0, min(pos.y(), area.height() - self.panel.height())))

    def mouseReleaseEvent(self, event):
        self.offset = None


class NotePanel(QFrame):
    def __init__(self, shell, path):
        super().__init__(shell.surface)
        self.shell, self.path, self.project = shell, path, shell.folder
        self.minimized = False
        self.colors = palette_for(shell.vault, path.parent)
        self.wallpaper = wallpaper_for(shell.vault, path)
        self.original = shell.vault.read(path)
        self.setObjectName('note')
        self.setStyleSheet(self.colors.css())
        self.setMinimumSize(360, 250)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 8)
        top = QHBoxLayout()
        self.caption = DragTitle(path.stem, self)
        top.addWidget(self.caption, 1)
        self.edit_button = button('Editar', self.toggle_edit)
        top.addWidget(self.edit_button)
        self.save_button = button('Guardar', self.save)
        self.save_button.hide()
        top.addWidget(self.save_button)
        minimize = button('—', self.minimize); minimize.setAccessibleName('Minimizar nota')
        close = button('×', self.close_note); close.setAccessibleName('Cerrar nota')
        top.addWidget(minimize); top.addWidget(close)
        layout.addLayout(top)
        self.pages = QStackedWidget()
        self.reader = SafeReader()
        self.reader.setOpenLinks(False)
        self.reader.setOpenExternalLinks(False)
        self.reader.document().setBaseUrl(QUrl.fromLocalFile(str(path.parent) + '/'))
        self.reader.document().setDefaultStyleSheet('a { color: ' + self.colors.accent + '; }')
        self.render_markdown(shell.vault.markdown(path))
        self.reader.anchorClicked.connect(lambda url: shell.follow_link(url, path))
        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName('Editar nota Markdown')
        self.editor.setPlainText(self.original)
        self.editor.textChanged.connect(self.changed)
        self.pages.addWidget(self.reader); self.pages.addWidget(self.editor)
        layout.addWidget(self.pages, 1)
        footer = QHBoxLayout()
        self.state = label('Lectura · ' + str(path.relative_to(shell.vault.root)), 'muted')
        self.state.setWordWrap(True)
        footer.addWidget(self.state, 1); footer.addWidget(QSizeGrip(self))
        layout.addLayout(footer)
        self.save_shortcut = QShortcut(QKeySequence('Ctrl+S'), self)
        self.save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.save_shortcut.activated.connect(self.save)

    @property
    def dirty(self):
        return self.editor.toPlainText() != self.original

    def render_markdown(self, markdown):
        self.reader.setMarkdown(markdown)
        block = self.reader.document().begin()
        anchors = []
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid() and fragment.charFormat().isAnchor():
                    anchors.append((fragment.position(), fragment.length()))
                it += 1
            block = block.next()
        for position, length in anchors:
            cursor = QTextCursor(self.reader.document())
            cursor.setPosition(position)
            cursor.setPosition(position + length, QTextCursor.MoveMode.KeepAnchor)
            style = QTextCharFormat(); style.setForeground(QColor(self.colors.accent))
            style.setFontUnderline(True); cursor.mergeCharFormat(style)

    def changed(self):
        self.caption.setText(self.path.stem + (' *' if self.dirty else ''))
        self.state.setText('Cambios sin guardar · Ctrl+S' if self.dirty else 'Guardado · ' + self.path.name)

    def toggle_edit(self):
        editing = self.pages.currentWidget() != self.editor
        if not editing:
            self.render_markdown(self.editor.toPlainText() if self.dirty else self.shell.vault.markdown(self.path))
        self.pages.setCurrentWidget(self.editor if editing else self.reader)
        self.edit_button.setText('Vista previa' if editing else 'Editar')
        self.save_button.setVisible(editing or self.dirty)
        self.pages.currentWidget().setFocus()
        if not self.dirty:
            self.state.setText('Markdown · Ctrl+S para guardar' if editing else 'Lectura · ' + self.path.name)

    def save(self):
        if not self.dirty:
            return True
        try:
            text = self.editor.toPlainText()
            self.shell.vault.save_note(self.path, text, self.original)
            self.original = text
            self.changed()
            self.render_markdown(self.shell.vault.markdown(self.path))
            self.shell.status.setText('Guardado: ' + self.path.name)
            return True
        except (OSError, ValueError) as error:
            self.state.setText(str(error))
            return False

    def can_close(self):
        if not self.dirty:
            return True
        self.restore()
        answer = QMessageBox.question(self, 'Cambios sin guardar', '¿Guardar los cambios de «' + self.path.stem + '»?',
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        return self.save() if answer == QMessageBox.StandardButton.Save else answer == QMessageBox.StandardButton.Discard

    def minimize(self):
        self.minimized = True
        self.hide()
        self.shell.update_dock()

    def restore(self):
        self.minimized = False
        self.show(); self.raise_()
        self.pages.currentWidget().setFocus()
        self.shell.update_dock()

    def close_note(self):
        if not self.can_close():
            return
        self.shell.panels.pop(self.path, None)
        self.hide(); self.deleteLater()
        self.shell.update_dock()
        self.shell.surface.setFocus()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath(); clip.addRoundedRect(rect, 12, 12); p.setClipPath(clip)
        paint_wallpaper(p, rect, self.wallpaper, self.colors.panel, 155)
        p.setPen(QPen(QColor(self.colors.border), 1.5)); p.drawRoundedRect(rect, 12, 12)


class MapNode(QPushButton):
    def __init__(self, surface, path=None, center=False):
        super().__init__(surface)
        self.surface, self.path, self.center = surface, path, center
        self.title, self.subtitle = '', ''
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Carpeta actual' if center else path.name)
        if not center:
            self.clicked.connect(lambda: surface.shell.activate(path))
            self.setToolTip(str(path.relative_to(surface.shell.vault.root)))

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = self.surface.shell.colors
        fill = QColor(colors.hover if self.underMouse() or self.hasFocus() else colors.card)
        fill.setAlpha(235 if self.center else 220)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setBrush(fill); p.setPen(QPen(QColor(colors.accent if self.hasFocus() else colors.border), 1.2))
        p.drawRoundedRect(rect, 13, 13)
        kind = 'folder' if self.center or self.path.is_dir() else 'note'
        draw_symbol(p, QRectF(self.width() / 2 - 10, 10, 20, 20), kind, colors.accent)
        p.setPen(QColor(colors.text))
        p.setFont(QFont('DejaVu Sans', 13 if self.center else 10, QFont.Weight.Bold if self.center else QFont.Weight.Normal))
        text = self.fontMetrics().elidedText(self.title, Qt.TextElideMode.ElideRight, (self.width() - 28) * 2)
        p.drawText(QRectF(10, 34, self.width() - 20, self.height() - 59), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
        p.setFont(QFont('DejaVu Sans', 8)); p.setPen(QColor(colors.muted))
        p.drawText(QRectF(8, self.height() - 22, self.width() - 16, 17), Qt.AlignmentFlag.AlignCenter, self.subtitle)


class Surface(QWidget):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.nodes = []
        self.setMinimumSize(640, 340)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.center = MapNode(self, center=True)
        self.center.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def arrange(self):
        width, height = self.width(), self.height()
        nw = max(134, min(190, int(width * .17)))
        nh = max(80, min(108, int(height * .21)))
        cw = max(166, min(226, int(width * .2)))
        self.center.setGeometry((width - cw) // 2, (height - nh - 8) // 2, cw, nh + 8)
        rx, ry = max(180, width * .36), max(110, height * .37)
        for index, widget in enumerate(self.nodes):
            angle = -math.pi / 2 + index * 2 * math.pi / max(1, len(self.nodes))
            cx = width / 2 + math.cos(angle) * rx
            cy = height / 2 + math.sin(angle) * ry
            widget.setGeometry(round(cx - nw / 2), round(cy - nh / 2), nw, nh)
        for panel in self.shell.panels.values():
            panel.resize(min(panel.width(), width), min(panel.height(), height))
            panel.move(max(0, min(panel.x(), width - panel.width())), max(0, min(panel.y(), height - panel.height())))
        self.update()

    def resizeEvent(self, event):
        self.arrange()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.shell.colors.accent); color.setAlpha(130)
        p.setPen(QPen(color, 1.2))
        origin = QPointF(self.width() / 2, self.height() / 2)
        for widget in self.nodes:
            end = QPointF(widget.geometry().center())
            path = QPainterPath(origin)
            path.cubicTo(QPointF((origin.x() + end.x()) / 2, origin.y()), QPointF(end.x(), (origin.y() + end.y()) / 2), end)
            p.drawPath(path)


class Explorer(QDialog):
    def __init__(self, shell):
        super().__init__(shell)
        self.shell, self.folder = shell, shell.folder
        self.setWindowTitle('Explorar proyectos'); self.resize(660, 510)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(button('↑ Subir', self.go_up))
        row.addWidget(button('Todos los proyectos', lambda: self.go(shell.vault.root)))
        row.addStretch()
        row.addWidget(button('Ver mapa', self.show_map)); layout.addLayout(row)
        self.location = label('', 'muted'); layout.addWidget(self.location)
        self.search = QLineEdit(); self.search.setPlaceholderText('Buscar notas en esta carpeta…')
        self.search.textChanged.connect(self.refresh); layout.addWidget(self.search)
        self.items = QListWidget(); self.items.setStyleSheet('QListWidget { border: none; background: transparent; }')
        self.items.itemActivated.connect(self.activate); layout.addWidget(self.items)
        row = QHBoxLayout()
        row.addWidget(button('Nueva nota', self.new_note)); row.addWidget(button('Nueva carpeta', self.new_folder))
        row.addStretch(); row.addWidget(button('Abrir', lambda: self.activate(self.items.currentItem())))
        layout.addLayout(row); self.refresh()

    def go(self, folder):
        self.folder = folder; self.search.clear(); self.refresh()

    def go_up(self):
        if self.folder != self.shell.vault.root:
            self.go(self.folder.parent)

    def refresh(self):
        self.items.clear()
        self.location.setText('Proyectos / ' + str(self.folder.relative_to(self.shell.vault.root)))
        try:
            entries = self.shell.vault.search(self.search.text(), self.folder) if self.search.text().strip() else self.shell.vault.entries(self.folder)
            for path in entries:
                item = QListWidgetItem(str(path.relative_to(self.folder)) if self.search.text().strip() else path.name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setIcon(symbol_icon('folder' if path.is_dir() else 'note', self.shell.colors.accent))
                self.items.addItem(item)
        except (OSError, ValueError) as error:
            self.location.setText(str(error))

    def activate(self, item):
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path.is_dir():
            self.go(path)
        else:
            self.shell.navigate(self.folder); self.shell.open_note(path); self.accept()

    def show_map(self):
        self.shell.navigate(self.folder); self.accept()

    def new_note(self):
        self.shell.new_note(folder=self.folder); self.refresh()

    def new_folder(self):
        self.shell.new_folder(folder=self.folder); self.refresh()


class Desktop(QMainWindow):
    PAGE_SIZE = 8

    def __init__(self, root, kiosk=False, system_session=False):
        super().__init__()
        self.vault = Vault(root)
        self.folder = self.vault.root
        self.kiosk = kiosk
        self.system_session = system_session and Path('/etc/prosperus-vm').is_file()
        self.panels = {}
        self.page = 0
        self.colors = Palette()
        self.apps = ApplicationService(self)
        self.apps.failed.connect(lambda error: self.status.setText(error))
        self.apps.favorites_changed.connect(self.update_dock)
        self.project_paths = []
        self.setWindowTitle('PrOSperus desktop')
        self.resize(1360, 850)
        self.setMinimumSize(860, 650)
        self.background = Wallpaper()
        self.setCentralWidget(self.background)
        layout = QVBoxLayout(self.background)
        layout.setContentsMargins(42, 26, 36, 18)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        identity = QVBoxLayout(); identity.setSpacing(5)
        identity.addWidget(label('E S C R I T O R I O   D E   P R O Y E C T O S', 'eyebrow'))
        self.title = label('', 'title'); identity.addWidget(self.title)
        self.breadcrumb = label('', 'muted'); identity.addWidget(self.breadcrumb)
        heading.addLayout(identity, 1)
        actions = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(button('Carpetas', self.toggle_projects))
        row.addWidget(button('Explorar', self.open_explorer))
        row.addWidget(button('Nueva nota', self.new_note))
        row.addWidget(button('Nueva carpeta', self.new_folder))
        actions.addLayout(row)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Buscar notas del proyecto…  Ctrl+L')
        self.search.setAccessibleName('Buscar notas')
        self.search.textChanged.connect(self.search_changed); actions.addWidget(self.search)
        heading.addLayout(actions)
        layout.addLayout(heading)
        self.surface = Surface(self); layout.addWidget(self.surface, 1)
        page_row = QHBoxLayout()
        self.up = button('↑ Subir', self.go_up); page_row.addWidget(self.up)
        page_row.addStretch()
        self.previous = button('‹ Anterior', lambda: self.change_page(-1))
        self.next = button('Siguiente ›', lambda: self.change_page(1))
        self.page_label = label('')
        page_row.addWidget(self.previous); page_row.addWidget(self.page_label); page_row.addWidget(self.next)
        page_row.addStretch()
        page_row.addWidget(button('Actualizar', self.refresh_projects))
        layout.addLayout(page_row)
        self.dock_frame = QFrame(); self.dock_frame.setObjectName('dock')
        dock_layout = QHBoxLayout(self.dock_frame); dock_layout.setContentsMargins(12, 10, 12, 10)
        self.dock_scroll = QScrollArea(); self.dock_scroll.setWidgetResizable(True)
        self.dock_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.dock_scroll.setFixedHeight(62)
        self.dock_content = QWidget(); self.dock = QHBoxLayout(self.dock_content)
        self.dock.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.dock.setContentsMargins(0, 0, 0, 7); self.dock.setSpacing(8)
        self.dock_scroll.setWidget(self.dock_content); dock_layout.addWidget(self.dock_scroll)
        layout.addWidget(self.dock_frame)
        footer = QHBoxLayout()
        self.status = label('Cada carpeta, un espacio de trabajo.', 'muted'); self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        footer.addWidget(label('PrOSperus · ' + __version__, 'muted'))
        if self.system_session:
            for text, action in [('Reiniciar', 'reboot'), ('Apagar', 'poweroff')]:
                footer.addWidget(button(text, lambda checked=False, a=action: self.ask_power(a)))
        layout.addLayout(footer)
        self.power_box = QWidget(); self.power_row = QHBoxLayout(self.power_box)
        layout.addWidget(self.power_box); self.power_box.hide()
        self.drawer = ProjectDrawer(self)
        self.edge = ProjectEdge(self)
        self.shortcuts = []
        self.shortcut('Escape', self.close_top_note)
        self.shortcut('Ctrl+L', self.search.setFocus)
        self.shortcut('Ctrl+O', self.open_first_note)
        self.shortcut('Ctrl+N', self.new_note)
        self.shortcut('Ctrl+Home', lambda: self.navigate(self.vault.root))
        self.shortcut('Ctrl+B', self.toggle_projects)
        self.refresh_projects()
        for index in range(9):
            self.shortcut(f'Ctrl+{index + 1}', lambda i=index: self.open_project_index(i))
        self.apply_appearance()
        print('PROSPERUS_READY ' + __version__, flush=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'drawer'):
            self.drawer.setGeometry(0, 0, min(370, self.width() - 100), self.background.height())
            self.edge.setGeometry(0, self.background.height() // 2 - 45, 25, 90)
            self.drawer.raise_()

    def shortcut(self, key, callback):
        item = QShortcut(QKeySequence(key), self); item.activated.connect(callback); self.shortcuts.append(item)

    def apply_appearance(self):
        self.colors = palette_for(self.vault, self.folder)
        self.setStyleSheet(self.colors.css())
        self.background.palette = self.colors
        self.background.wallpaper = wallpaper_for(self.vault, self.folder)
        self.background.update(); self.surface.update()

    def refresh_projects(self):
        self.project_paths = [p for p in self.vault.entries(self.vault.root) if p.is_dir()]
        self.render(); self.update_dock()
        if self.drawer.isVisible():
            self.drawer.filter_projects()

    def open_project_index(self, index):
        if index < len(self.project_paths):
            self.navigate(self.project_paths[index])

    def toggle_projects(self):
        self.drawer.hide() if self.drawer.isVisible() else self.drawer.reveal()

    def open_explorer(self):
        Explorer(self).exec()

    def open_applications(self):
        ApplicationBrowser(self).exec()

    def navigate(self, folder):
        try:
            folder = self.vault.checked(folder)
            if not folder.is_dir():
                raise ValueError('Selecciona una carpeta.')
            self.folder = folder; self.page = 0
            self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
            self.apply_appearance(); self.render()
            for panel in self.panels.values():
                panel.setVisible(panel.project == self.folder and not panel.minimized)
            self.update_dock()
            if self.drawer.isVisible():
                self.drawer.refresh()
        except (OSError, ValueError) as error:
            self.status.setText(str(error))

    def go_up(self):
        if self.folder != self.vault.root:
            self.navigate(self.folder.parent)

    def search_changed(self):
        self.page = 0; self.render()

    def change_page(self, direction):
        self.page += direction; self.render()

    def render(self):
        try:
            entries = self.vault.search(self.search.text(), self.folder) if self.search.text().strip() else self.vault.entries(self.folder)
        except (OSError, ValueError) as error:
            self.status.setText(str(error)); entries = []
        self.title.setText(self.folder.name if self.folder != self.vault.root else 'Tus proyectos')
        relative = self.folder.relative_to(self.vault.root)
        self.breadcrumb.setText(' / '.join(relative.parts) if relative.parts else 'Carpetas, ideas y notas en un mismo lugar')
        self.up.setEnabled(self.folder != self.vault.root)
        self.page = max(0, min(self.page, (len(entries) - 1) // self.PAGE_SIZE))
        for item in self.surface.nodes:
            item.hide(); item.deleteLater()
        self.surface.nodes = []
        for path in entries[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]:
            item = MapNode(self.surface, path)
            item.title = path.name if path.is_dir() else path.stem
            item.setText(item.title)
            item.subtitle = 'Abrir carpeta' if path.is_dir() else 'Abrir nota'
            item.show(); self.surface.nodes.append(item)
        self.surface.center.title = self.title.text()
        self.surface.center.subtitle = f'{len(entries)} archivos y carpetas' if entries else 'Crea tu primera nota'
        self.page_label.setText(f'{self.page + 1} / {max(1, math.ceil(len(entries) / self.PAGE_SIZE))}')
        self.previous.setEnabled(self.page > 0); self.next.setEnabled((self.page + 1) * self.PAGE_SIZE < len(entries))
        self.surface.arrange()
        for panel in self.panels.values():
            if panel.isVisible():
                panel.raise_()

    def activate(self, path):
        self.navigate(path) if path.is_dir() else self.open_note(path)

    def open_note(self, path, edit=False):
        try:
            path = self.vault.checked(path)
            if path in self.panels:
                panel = self.panels[path]; panel.project = self.folder
            else:
                panel = NotePanel(self, path); self.panels[path] = panel
                panel.resize(min(660, self.surface.width()), min(470, self.surface.height()))
                panel.move(max(0, self.surface.width() - panel.width() - 24), min(24 * (len(self.panels) % 4), max(0, self.surface.height() - panel.height())))
            panel.restore()
            if edit and panel.pages.currentWidget() != panel.editor:
                panel.toggle_edit(); panel.editor.moveCursor(QTextCursor.MoveOperation.End)
            self.status.setText(str(path.relative_to(self.vault.root)))
        except (OSError, ValueError, UnicodeError) as error:
            self.status.setText(str(error))

    def new_note(self, checked=False, folder=None):
        folder = folder or self.folder
        name, ok = QInputDialog.getText(self, 'Nueva nota', 'Nombre de la nota:')
        if ok:
            try:
                path = self.vault.create_note(folder, name)
                self.navigate(folder); self.open_note(path, edit=True); self.refresh_projects()
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'No se pudo crear la nota', str(error))

    def new_folder(self, checked=False, folder=None):
        folder = folder or self.folder
        name, ok = QInputDialog.getText(self, 'Nueva carpeta', 'Nombre de la carpeta:')
        if ok:
            try:
                path = self.vault.create_folder(folder, name)
                self.navigate(path); self.refresh_projects()
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'No se pudo crear la carpeta', str(error))

    def follow_link(self, url, source):
        try:
            path = self.vault.resolve_note(url.toString(), source); self.open_note(path)
            if url.fragment() and path in self.panels:
                self.panels[path].reader.scrollToAnchor(url.fragment())
        except (OSError, ValueError) as error:
            self.status.setText(str(error))

    def open_first_note(self):
        notes = list(self.vault.notes(self.folder))
        if notes:
            self.open_note(notes[0])

    def close_top_note(self):
        if self.drawer.isVisible():
            self.drawer.hide(); return
        visible = [p for p in self.surface.children() if isinstance(p, NotePanel) and p.isVisible()]
        if visible:
            visible[-1].close_note()
        else:
            self.search.clear(); self.power_box.hide()

    def update_dock(self):
        while self.dock.count():
            item = self.dock.takeAt(0)
            if item.widget():
                item.widget().hide(); item.widget().deleteLater()
        def add_access(item):
            self.dock.addWidget(item)
            item.ensurePolished()
            icon_width = item.iconSize().width() + 8 if not item.icon().isNull() else 0
            available = 260 - 34 - icon_width
            full_text = item.text()
            item.setText(item.fontMetrics().elidedText(full_text, Qt.TextElideMode.ElideRight, available))
            item.setAccessibleName(full_text)
            item.setFixedWidth(max(110, item.fontMetrics().horizontalAdvance(item.text()) + 34 + icon_width))
        add_access(button('Aplicaciones', self.open_applications))
        for app in self.apps.favorites:
            item = button('★ ' + app['name'], lambda checked=False, a=app: self.apps.run('launch', a['id']))
            item.setToolTip(app['name']); add_access(item)
        current = [p for p in self.panels.values() if p.project == self.folder]
        for panel in current:
            item = button(panel.path.stem, panel.restore)
            item.setIcon(symbol_icon('window', self.colors.accent)); item.setMaximumWidth(200)
            item.setToolTip(('Recuperar: ' if panel.minimized else 'Enfocar: ') + panel.path.stem)
            item.setObjectName('minimized' if panel.minimized else 'openNote')
            add_access(item)
        if current:
            divider = QFrame(); divider.setFrameShape(QFrame.Shape.VLine); divider.setFixedWidth(1)
            divider.setStyleSheet('background: ' + self.colors.border); self.dock.addWidget(divider)
        try:
            for path in self.vault.entries(self.folder):
                text = path.name if path.is_dir() else path.stem
                item = button(text if len(text) < 26 else text[:24] + '…', lambda checked=False, p=path: self.activate(p))
                item.setIcon(symbol_icon('folder' if path.is_dir() else 'note', self.colors.accent))
                item.setToolTip(text); add_access(item)
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
        self.dock.addStretch()

    def ask_power(self, action):
        if not self.system_session:
            return
        while self.power_row.count():
            item = self.power_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.power_row.addWidget(label('¿Reiniciar la VM?' if action == 'reboot' else '¿Apagar la VM?'))
        self.power_row.addWidget(button('Cancelar', self.power_box.hide))
        self.power_row.addWidget(button('Confirmar', lambda: self.power(action))); self.power_box.show()

    def power(self, action):
        if not self.system_session or action not in ('reboot', 'poweroff'):
            return
        if not all(panel.can_close() for panel in list(self.panels.values())):
            return
        check = subprocess.run(['systemd-detect-virt', '--vm', '--quiet'], check=False)
        if check.returncode:
            self.status.setText('Estos controles solo están disponibles en la VM PrOSperus.'); return
        result = subprocess.run(['systemctl', action], capture_output=True, text=True, timeout=15)
        if result.returncode:
            self.status.setText(result.stderr.strip() or 'No se pudo completar la acción.')

    def closeEvent(self, event):
        if self.kiosk:
            event.ignore(); self.status.setText('Usa los controles de sesión para apagar.')
        elif all(panel.can_close() for panel in list(self.panels.values())):
            event.accept()
        else:
            event.ignore()


def main():
    parser = argparse.ArgumentParser(description='PrOSperus desktop — escritorio de proyectos')
    parser.add_argument('--root', type=Path, default=Path('/usr/share/prosperus/demo'))
    parser.add_argument('--kiosk', action='store_true')
    parser.add_argument('--system-session', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1]); app.setApplicationName('PrOSperus desktop')
    app.setStyleSheet(STYLE)
    try:
        desktop = Desktop(args.root, args.kiosk, args.system_session)
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + '\n')
    desktop.showFullScreen() if args.kiosk else desktop.show()
    if args.screenshot:
        def capture():
            desktop.grab().save(str(args.screenshot)); app.quit()
        QTimer.singleShot(500, capture)
    sys.exit(app.exec())
