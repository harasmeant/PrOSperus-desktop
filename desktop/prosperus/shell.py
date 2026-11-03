"""Project desktop following the accepted Obsidian visual reference."""
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import itertools
import os
import math
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QEasingCurve, QEvent, QFileSystemWatcher, QParallelAnimationGroup, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QPainterPath, QPen, QShortcut, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QInputDialog,
    QLabel, QLayout, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSizeGrip, QStackedWidget,
    QTextBrowser, QVBoxLayout, QWidget, QStyle)

from . import __version__
from .appearance import (Palette, Wallpaper, draw_symbol, paint_wallpaper,
                         palette_for, symbol_icon, wallpaper_for, wallpaper_traits)
from .model import Vault
from .corner_menu import HoverMenuButton
from .quick_settings import QuickSettings
from PySide6.QtWidgets import QWidgetAction
from . import motion
from .branches import branch, flourish
from . import branch_style
from .map_layout import link_order, map_metrics, radial_slots, nearest_in_direction, separate
from .projects import ProjectDrawer, ProjectEdge
from .launcher import ApplicationBrowser, ApplicationService
from .window_manager import WindowManager
from .window_controls import HoverControls
from .window_layouts import LayoutOptions, Rect, arrange, screen_profile
from .file_actions import FileActions, local_paths
from .desktop_keys import DesktopKeys, SHORTCUT_HELP
from .controls import ControlsDialog, SessionControls
from .layout_settings import LayoutDialog
from .accessibility import Accessibility, AccessibilityDialog
from .hardware import HardwareDialog

STYLE = Palette().css()


ICONS = {
    'Carpetas': 'folders',
    'Explorar': 'search',
    'Nueva nota': 'note-plus',
    'Nuevo proyecto': 'folder-plus',
    'Nueva carpeta': 'folder-plus',
    'Guardar': 'save',
    'Cerrar': 'close',
    'Aplicaciones': 'apps',
    'Controles': 'sliders',
    'Ayuda · F1': 'help',
    'Actualizar': 'refresh',
    'Apagar': 'power',
    'Reiniciar': 'restart',
}

def button(text, callback, parent=None):
    widget = QPushButton(text, parent)
    widget.clicked.connect(callback)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if text in ICONS:
        widget.setIcon(symbol_icon(ICONS[text], '#d4dbc8'))
    return widget


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    return widget


def ask_place(parent, vault, title, folder, ask_name=True):
    """Pide nombre y carpeta de destino; propone la carpeta actual. Devuelve (nombre, carpeta) o None."""
    dialog = QDialog(parent); dialog.setWindowTitle(title)
    form = QFormLayout(dialog)
    name = QLineEdit(dialog)
    if ask_name:
        form.addRow('Nombre:', name)
    places = QComboBox(dialog)
    for path in vault.folders():
        places.addItem('Tus proyectos' if path == vault.root else ' / '.join(path.relative_to(vault.root).parts), path)
    places.setCurrentIndex(max(0, places.findData(folder)))
    form.addRow('Proyecto o carpeta:', places)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    (name if ask_name else places).setFocus()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return name.text(), places.currentData()


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


# Opacidad del fondo de las notas (a petición: 40 % de transparencia).
NOTE_OPACITY = .6


class NotePanel(QFrame):
    def __init__(self, shell, path):
        super().__init__(shell.surface)
        self.shell, self.path, self.project = shell, path, shell.folder
        self.minimized = False
        self.colors = shell.accessibility.palette(palette_for(shell.vault, path.parent))
        self.wallpaper = None if shell.accessibility.high_contrast else wallpaper_for(shell.vault, path)
        self.original = shell.vault.read(path)
        self.setObjectName('note')
        self.setStyleSheet(shell.accessibility.css(self.colors))
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
        self.normal_geometry = None
        # Puntos de ventana: crecen al pasar el ratón por la nota.
        self.controls = HoverControls(self, watch=self)
        self.controls.triggered.connect(lambda action: {'minimize': self.minimize, 'maximize': self.toggle_maximized,
                                                         'close': self.close_note}[action]())
        top.addWidget(self.controls)
        layout.addLayout(top)
        layout.addSpacing(12)  # sitio para el remate floral bajo el título
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
        # El nombre ya está en la cabecera del panel: no repetir un primer título igual.
        first, _, rest = markdown.lstrip().partition('\n')
        if first.startswith('# ') and first[2:].strip() == self.path.stem:
            markdown = rest
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

    def toggle_maximized(self, checked=False, maximized=None):
        """Ocupa todo el escritorio o vuelve al tamaño anterior."""
        maximized = self.normal_geometry is None if maximized is None else maximized
        if maximized:
            if self.normal_geometry is None:
                self.normal_geometry = self.geometry()
            self.setGeometry(self.shell.surface.rect())
        elif self.normal_geometry is not None:
            self.setGeometry(self.normal_geometry); self.normal_geometry = None
        self.controls.set_maximized(self.normal_geometry is not None)
        self.raise_()

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
        if self.shell.windows.mode == 'fibonacci':
            self.shell.arrange_notes()
        self.shell.update_dock()
        self.shell.surface.setFocus()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath(); clip.addRoundedRect(rect, 12, 12); p.setClipPath(clip)
        # Fondo al 60 % (40 % de transparencia): se ve el escritorio de detrás. Opaco en alto contraste.
        glass = QColor(self.colors.panel)
        glass.setAlphaF(1.0 if self.shell.accessibility.high_contrast else NOTE_OPACITY)
        p.fillRect(rect, glass)
        if not self.minimized and not self.shell.accessibility.high_contrast:
            # Remate floral bajo el título, en el estilo de las ramas del fondo de la nota.
            vine = QColor(self.colors.text); vine.setAlphaF(.28)
            traits = None
            if self.wallpaper:
                try:
                    traits = wallpaper_traits(self.wallpaper, self.wallpaper.stat().st_mtime_ns)
                except OSError:
                    pass
            flourish(p, rect.left() + 18, rect.right() - 18, self.pages.geometry().top() - 9, vine,
                     len(self.path.stem), traits)
        p.setPen(QPen(QColor(self.colors.border), 1.5)); p.drawRoundedRect(rect, 12, 12)


class MapNode(QPushButton):
    def __init__(self, surface, path=None, center=False):
        super().__init__(surface)
        self.surface, self.path, self.center = surface, path, center
        self.title, self.subtitle = '', ''
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Carpeta actual' if center else path.name)
        if not center:
            self.setToolTip(str(path.relative_to(surface.shell.vault.root)))

    def compact(self):
        return not self.center and self.path.is_dir() and not self.surface.expanding

    def mousePressEvent(self, event):
        if not self.center and event.button() == Qt.MouseButton.LeftButton:
            self.surface.select(self.path, bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
            self.press = event.position().toPoint()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        # Con el ratón encima, Enter abre esta tarjeta.
        if not self.center and self.surface.dragging is None:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().enterEvent(event)

    def mouseMoveEvent(self, event):
        press = getattr(self, 'press', None)
        if (press is not None and event.buttons() & Qt.MouseButton.LeftButton
                and (self.surface.dragging is self or (event.position().toPoint() - press).manhattanLength() >= QApplication.startDragDistance())):
            # Arrastrar la tarjeta por el escritorio; al soltar encaja en el hueco más cercano.
            self.surface.dragging = self; self.raise_()
            self.move(self.mapToParent(event.position().toPoint() - press)); self.surface.update()
            return
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event); return
        if self.center:
            # Doble clic en el centro: volver a la carpeta anterior.
            self.surface.close_node()
        elif not self.surface.shell.accessibility.single_click:
            self.surface.open_node(self)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.press = None
        if self.surface.dragging is self:
            self.setDown(False); self.surface.drop(self); event.accept(); return
        open_path = (not self.center and event.button() == Qt.MouseButton.LeftButton
                     and self.rect().contains(event.position().toPoint())
                     and event.modifiers() == Qt.KeyboardModifier.NoModifier
                     and self.surface.shell.accessibility.single_click)
        super().mouseReleaseEvent(event)
        if open_path:
            self.surface.open_node(self)

    def keyPressEvent(self, event):
        if not self.center and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.surface.open_node(self)
        elif not self.center and event.key() == Qt.Key.Key_Space:
            self.surface.select(self.path, bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            dir_map = {
                Qt.Key.Key_Left: 'left',
                Qt.Key.Key_Right: 'right',
                Qt.Key.Key_Up: 'up',
                Qt.Key.Key_Down: 'down'
            }
            self.surface.focus_direction(self.path, dir_map[event.key()])
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        if self.path and self.path not in self.surface.selection:
            self.surface.select(self.path)
        self.surface.show_menu(event.globalPos())

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = self.surface.shell.colors
        selected = self.path in self.surface.selection
        fill = QColor(colors.hover if selected or self.underMouse() or self.hasFocus() else colors.card)
        fill.setAlpha(255 if self.surface.shell.accessibility.high_contrast else (235 if self.center else 220))
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setBrush(fill); p.setPen(QPen(QColor(colors.accent if selected or self.hasFocus() else colors.border), 2.5 if selected else 1.2))
        p.drawRoundedRect(rect, 13, 13)
        if self.compact():
            # Carpeta del mapa: solo el nombre; su contenido sale en ramas.
            draw_symbol(p, QRectF(12, self.height() / 2 - 9, 18, 18), 'folder', colors.accent)
            p.setPen(QColor(colors.text))
            p.setFont(QFont('DejaVu Sans', self.surface.shell.accessibility.font_size(10), QFont.Weight.Bold))
            text = p.fontMetrics().elidedText(self.title, Qt.TextElideMode.ElideRight, self.width() - 46)
            p.drawText(QRectF(36, 0, self.width() - 44, self.height()), Qt.AlignmentFlag.AlignVCenter, text)
            return
        kind = 'folder' if self.center or self.path.is_dir() else 'note'
        draw_symbol(p, QRectF(self.width() / 2 - 10, 10, 20, 20), kind, colors.accent)
        p.setPen(QColor(colors.text))
        font_size = self.surface.shell.accessibility.font_size
        p.setFont(QFont('DejaVu Sans', font_size(13 if self.center else 10), QFont.Weight.Bold if self.center else QFont.Weight.Normal))
        text = p.fontMetrics().elidedText(self.title, Qt.TextElideMode.ElideRight, self.width() - 20)
        p.drawText(QRectF(10, 34, self.width() - 20, self.height() - 59), Qt.AlignmentFlag.AlignCenter, text)
        p.setFont(QFont('DejaVu Sans', font_size(8))); p.setPen(QColor(colors.muted))
        p.drawText(QRectF(8, self.height() - 22, self.width() - 16, 17), Qt.AlignmentFlag.AlignCenter, self.subtitle)


class LeafNode(QPushButton):
    """Archivo o subcarpeta que sale de una carpeta del mapa."""
    def __init__(self, surface, parent_node, path=None, more=0):
        super().__init__(surface)
        self.surface, self.parent_node, self.path = surface, parent_node, path
        self.text_value = f'+{more} más' if path is None else (path.name if path.is_dir() or path.suffix.lower() != '.md' else path.stem)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self.text_value if path is None else str(path.relative_to(surface.shell.vault.root)))
        self.setAccessibleName(self.text_value)
        self.clicked.connect(self.open)

    def open(self):
        # «+N más» entra en la carpeta; el resto abre el archivo o la subcarpeta.
        self.surface.open_node(self.parent_node) if self.path is None else self.surface.shell.activate(self.path)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = self.surface.shell.colors
        fill = QColor(colors.hover if self.underMouse() else colors.card); fill.setAlpha(200)
        p.setBrush(fill); p.setPen(QPen(QColor(colors.border), 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), self.height() / 2, self.height() / 2)
        if self.path is not None:
            draw_symbol(p, QRectF(8, self.height() / 2 - 7, 14, 14), 'folder' if self.path.is_dir() else 'note', colors.accent)
        p.setPen(QColor(colors.text if self.path is not None else colors.muted))
        p.setFont(QFont('DejaVu Sans', self.surface.shell.accessibility.font_size(8)))
        left = 26 if self.path is not None else 10
        text = p.fontMetrics().elidedText(self.text_value, Qt.TextElideMode.ElideRight, self.width() - left - 8)
        p.drawText(QRectF(left, 0, self.width() - left - 6, self.height()), Qt.AlignmentFlag.AlignVCenter, text)


class Surface(QWidget):
    LEAVES = 4
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.nodes = []
        self.selection = []
        self.setAcceptDrops(True)
        self.setMinimumSize(640, 340)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.leaves = []
        self.expanding = None
        self.dragging = None
        self.manual = {}  # carpeta → {ruta: hueco} elegido arrastrando (solo esta sesión)
        self.center = MapNode(self, center=True)
        self.center.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def build_leaves(self):
        """Crea las ramas de contenido de cada carpeta visible en el mapa."""
        for leaf in self.leaves:
            leaf.hide(); leaf.deleteLater()
        self.leaves = []
        for node in self.nodes:
            if not node.path.is_dir():
                continue
            try:
                inside = self.shell.vault.entries(node.path)
            except (OSError, ValueError):
                continue
            shown = inside[:self.LEAVES]
            for path in shown:
                self.leaves.append(LeafNode(self, node, path))
            if len(inside) > len(shown):
                self.leaves.append(LeafNode(self, node, more=len(inside) - len(shown)))
        for leaf in self.leaves:
            leaf.show()
        self.compute_links()

    def open_node(self, node):
        if not node.path.is_dir():
            self.shell.activate(node.path)
            return
        if getattr(self, 'morph', None) is not None:
            return
        # Geometrías iniciales antes de navegar
        start_center = QRect(node.geometry())
        leaf_starts = {
            leaf.path: leaf.geometry().center()
            for leaf in self.leaves
            if leaf.parent_node is node and leaf.path is not None
        }
        # Navega y reconstruye el mapa
        self.shell.navigate(node.path)
        if self.shell.folder != node.path:
            return
        # Oculta hojas durante la animación
        for leaf in self.leaves:
            leaf.hide()
        # Grupo de animaciones paralelas
        group = QParallelAnimationGroup(self)
        # Animación del centro
        center_anim = QPropertyAnimation(self.center, b'geometry', self)
        center_anim.setDuration(450)
        center_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        center_anim.setStartValue(start_center)
        center_anim.setEndValue(self.center.geometry())
        center_anim.valueChanged.connect(lambda *_: self.update())
        group.addAnimation(center_anim)
        # Animaciones de los nodos
        for n in self.nodes:
            final_geo = n.geometry()
            start_pos = leaf_starts.get(n.path, start_center.center())
            start_rect = QRect(start_pos, final_geo.size())
            start_rect.moveCenter(start_pos)
            anim = QPropertyAnimation(n, b'geometry', self)
            anim.setDuration(450)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(start_rect)
            anim.setEndValue(final_geo)
            anim.valueChanged.connect(lambda *_: self.update())
            group.addAnimation(anim)
        # Limpieza al terminar
        def finished():
            self.morph = None
            for leaf in self.leaves:
                leaf.show()
            self.arrange()
            motion.fade_in(self.leaves, 220, 18, self.update)
            topmost = min(self.nodes, key=lambda n: n.geometry().y()) if self.nodes else None
            self.select_widget(topmost)
            self.update()
        group.finished.connect(finished)
        self.morph = group
        group.start()

    def slide_page(self, direction):
        """Cambio de página: las tarjetas entran desde el lado al que se avanza, con fundido."""
        moving = [w for w in self.nodes + self.leaves if w.isVisible()]
        for widget in moving:
            motion.slide_in(widget, QPoint(90 * direction, 0), 300).valueChanged.connect(lambda *_: self.update())
        motion.fade_in(moving, 240, 14, self.update)

    def select(self, path, toggle=False):
        if toggle:
            if path in self.selection:
                self.selection.remove(path)
            else:
                self.selection.append(path)
        else:
            self.selection = [path] if path else []
        for node in self.nodes:
            node.update()
        self.shell.status.setText(f'{len(self.selection)} seleccionados · Ctrl+C copiar · Ctrl+V pegar · Doble clic para abrir')

    def select_all(self):
        self.selection = [node.path for node in self.nodes]
        for node in self.nodes:
            node.update()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            dir_map = {
                Qt.Key.Key_Left: 'left',
                Qt.Key.Key_Right: 'right',
                Qt.Key.Key_Up: 'up',
                Qt.Key.Key_Down: 'down'
            }
            self.focus_direction(self.selection[-1] if self.selection else None, dir_map[event.key()])
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and len(self.selection) == 1:
            self.shell.activate(self.selection[0])
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.select(None); self.setFocus()
        super().mousePressEvent(event)

    def show_menu(self, position):
        menu = self.shell.files.menu(self, list(self.selection), self.shell.folder)
        menu.exec(position); menu.deleteLater()

    def contextMenuEvent(self, event):
        self.show_menu(event.globalPos())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction); event.accept()

    def dropEvent(self, event):
        try:
            paths = local_paths(event.mimeData())
            if paths:
                node = self.childAt(event.position().toPoint())
                destination = node.path if isinstance(node, MapNode) and node.path and node.path.is_dir() else self.shell.folder
                self.shell.files.transfer(paths, destination)
                event.setDropAction(Qt.DropAction.CopyAction); event.accept()
        except ValueError as error:
            self.shell.status.setText(str(error))

    def arrange(self):
        width, height = self.width(), self.height()
        m = map_metrics(width, height)
        nw, nh, cw, fw, fh, lw, lh = (m[k] for k in ('nw', 'nh', 'cw', 'fw', 'fh', 'lw', 'lh'))
        self.center.setGeometry((width - cw) // 2, (height - nh - 8) // 2, cw, nh + 8)

        def clamp(x, y, w, h):
            return QRect(round(max(4, min(width - w - 4, x - w / 2))), round(max(4, min(height - h - 4, y - h / 2))), w, h)

        # Radios equiespaciados (3, 4, … hasta PAGE_SIZE por página, como en el prototipo).
        # Los enlaces solo deciden el orden: las notas más enlazadas caen en radios vecinos.
        self.slots = radial_slots(len(self.nodes), width / 2, height / 2, m['rx'], m['ry'])
        manual = self.manual.setdefault(self.shell.folder, {})
        self.slot_of, used = {}, set()
        for widget in self.nodes:
            index = manual.get(widget.path)
            if index is not None and index < len(self.slots) and index not in used:
                self.slot_of[widget] = index; used.add(index)
        free = (i for i in range(len(self.slots)) if i not in used)
        for i in link_order(len(self.nodes), getattr(self, 'link_weights', None) or {}):
            if self.nodes[i] not in self.slot_of:
                self.slot_of[self.nodes[i]] = next(free)

        fixed = [(self.center.x(), self.center.y(), self.center.width(), self.center.height())]
        for widget in self.nodes:
            cx, cy = self.slots[self.slot_of[widget]]
            if widget is self.expanding or widget is self.dragging:
                continue
            w, h = (fw, fh) if widget.path.is_dir() else (nw, nh)
            rect = clamp(cx, cy, w, h); widget.setGeometry(rect)
            fixed.append((rect.x(), rect.y(), rect.width(), rect.height()))
            # Hojas de la carpeta: hacia fuera, en la dirección de su hueco.
            leaves = [leaf for leaf in self.leaves if leaf.parent_node is widget]
            angle = math.atan2(cy - height / 2, cx - width / 2)
            dx, dy = math.cos(angle), math.sin(angle)
            horizontal = abs(dx) > abs(dy)
            outward = cx + dx * (fw / 2 + lw / 2 + 50)
            if horizontal and not lw / 2 + 4 <= outward <= width - lw / 2 - 4:
                # Sin sitio hacia fuera (pantallas estrechas): las hojas van debajo o encima de la tarjeta.
                horizontal, dx, dy = False, 0.0, (1.0 if cy >= height / 2 else -1.0)
            gap = lh + 8 if horizontal else lw + 10
            distance = (fw / 2 + lw / 2 + 50) if horizontal else (fh / 2 + lh / 2 + 56)
            for j, leaf in enumerate(leaves):
                offset = (j - (len(leaves) - 1) / 2) * gap
                leaf.setGeometry(clamp(cx + dx * distance + (0 if horizontal else offset),
                                       cy + dy * distance + (offset if horizontal else 0), lw, lh))

        # Solo se apartan las hojas: las tarjetas se quedan en su hueco de la rejilla.
        leaves = [leaf for leaf in self.leaves if leaf.isVisible() and leaf.parent_node is not self.expanding]
        rects = separate([(l.x(), l.y(), l.width(), l.height()) for l in leaves], fixed=fixed,
                         bounds=(4, 4, width - 8, height - 8), gap=10)
        for leaf, rect in zip(leaves, rects):
            leaf.setGeometry(QRect(*rect))

        for panel in self.shell.panels.values():
            panel.resize(min(panel.width(), width), min(panel.height(), height))
            panel.move(max(0, min(panel.x(), width - panel.width())), max(0, min(panel.y(), height - panel.height())))
        self.update()

    def drop(self, widget):
        self.dragging = None
        here = widget.geometry().center()
        # Soltar una nota encima de una carpeta la mueve dentro; las carpetas solo cambian de hueco.
        folder = widget.path.is_file() and next((w for w in self.nodes + self.leaves if w is not widget and w.isVisible()
                       and getattr(w, 'path', None) is not None and w.path.is_dir() and w.geometry().contains(here)), None)
        if folder:
            self.arrange(); self.shell.move_to([widget.path], folder.path); return
        target = min(range(len(self.slots)), key=lambda i: (self.slots[i][0] - here.x()) ** 2 + (self.slots[i][1] - here.y()) ** 2)
        manual = self.manual.setdefault(self.shell.folder, {})
        manual.update({w.path: i for w, i in self.slot_of.items()})
        other = next((w for w, i in self.slot_of.items() if i == target and w is not widget), None)
        if other is not None:
            manual[other.path] = self.slot_of[widget]  # intercambian sus huecos
        manual[widget.path] = target
        self.arrange()

    def resizeEvent(self, event):
        self.arrange()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Enredadera monocroma (tono nácar): troncos en S que se afinan, zarcillos y hojas.
        origin = QPointF(self.center.geometry().center())
        pearl = QColor(self.shell.colors.text)
        # Estilo procedural: sale del fondo de la carpeta y solo cambia si cambia el archivo.
        source = self.shell.background.wallpaper
        try:
            traits = wallpaper_traits(source, source.stat().st_mtime_ns) if source else None
        except OSError:
            traits = None
        # Ajustes personales de la carpeta (aplicación «Ramas») encima de lo que dice el fondo.
        traits = branch_style.merge(traits, branch_style.load(self.shell.folder, self.shell.vault.root))
        opacity = traits.get('opacity', 1)
        alpha = lambda value: max(0, min(255, round(value * opacity)))
        # Las ramas nacen en el borde de las tarjetas: no se ven a través de ellas.
        visible = QPainterPath(); visible.addRect(QRectF(self.rect()))
        for card in [self.center] + self.nodes + [leaf for leaf in self.leaves if leaf.isVisible()]:
            hole = QPainterPath(); hole.addRoundedRect(QRectF(card.geometry()), 10, 10)
            visible = visible.subtracted(hole)
        p.setClipPath(visible)

        def faded(widget):
            # Mientras una tarjeta aparece con fundido, su rama la acompaña (no llega antes que ella).
            effect = widget.graphicsEffect()
            return effect.opacity() if isinstance(effect, QGraphicsOpacityEffect) else 1.0
        for k, widget in enumerate(self.nodes):
            pearl.setAlpha(alpha(165 * faded(widget)))
            branch(p, origin, QPointF(widget.geometry().center()), 7.5, 2.2, pearl, k, 5, traits=traits)
        for k, leaf in enumerate(self.leaves):
            if leaf.isVisible():
                pearl.setAlpha(alpha(120 * faded(leaf)))
                branch(p, QPointF(leaf.parent_node.geometry().center()), QPointF(leaf.geometry().center()), 2.4, .9, pearl, k, 1, .12, traits)
        # Enlaces entre notas: zarcillo fino entre vecinos, más grueso cuanto más enlazadas.
        node_index = {n: i for i, n in enumerate(self.nodes)}
        for k, (wa, wb) in enumerate(getattr(self, 'link_pairs', [])):
            if not wa.isVisible() or not wb.isVisible():
                continue
            width = 1.6
            if wa in node_index and wb in node_index:
                i, j = node_index[wa], node_index[wb]
                width = 1.6 + .7 * min(self.link_weights.get((min(i, j), max(i, j)), 1), 5)
            pearl.setAlpha(alpha(140 * min(faded(wa), faded(wb))))
            branch(p, QPointF(wa.geometry().center()), QPointF(wb.geometry().center()), width, width * .6, pearl, k, 2, .25, traits)

    def focus_direction(self, path, direction):
        centers = []
        for node in self.nodes:
            rect = node.geometry()
            centers.append((rect.center().x(), rect.center().y()))
        selected = None
        for node in self.nodes:
            if node.path == path:
                selected = node
                break
        if selected is None:
            # Sin selección: partir del centro del Surface para buscar el siguiente nodo
            rect = self.center.geometry()
            origin = (rect.center().x(), rect.center().y())
            idx = nearest_in_direction(centers, origin, direction)
            if idx is not None:
                node = self.nodes[idx]
                self.select(node.path)
                node.setFocus()
            return
        # Las flechas solo mueven la selección; Enter abre y Retroceso vuelve atrás.
        srect = selected.geometry()
        others = [node for node in self.nodes if node is not selected]
        idx = nearest_in_direction([(n.geometry().center().x(), n.geometry().center().y()) for n in others],
                                   (srect.center().x(), srect.center().y()), direction)
        if idx is not None:
            self.select(others[idx].path)
            others[idx].setFocus()

    def close_node(self):
        """Reverso de open_node: el centro vuelve a su sitio y el resto sale del centro."""
        if getattr(self, 'morph', None) is not None:
            return
        folder = self.shell.folder
        if folder == self.shell.vault.root:
            return
        start_center = QRect(self.center.geometry())
        self.shell.go_up()
        if self.shell.folder != folder.parent:
            return
        for leaf in self.leaves:
            leaf.hide()
        group = QParallelAnimationGroup(self)
        middle = self.center.geometry().center()
        for n in self.nodes:
            final = n.geometry()
            if n.path == folder:
                start = QRect(start_center)
            else:
                start = QRect(final); start.moveCenter(middle)
            anim = QPropertyAnimation(n, b'geometry', self)
            anim.setDuration(450); anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(start); anim.setEndValue(final)
            anim.valueChanged.connect(lambda *_: self.update())
            group.addAnimation(anim)

        def finished():
            self.morph = None
            for leaf in self.leaves:
                leaf.show()
            self.arrange()
            motion.fade_in(self.leaves, 220, 18, self.update)
            for n in self.nodes:
                if n.path == folder:
                    self.select_widget(n)
                    break
            self.update()
        group.finished.connect(finished)
        self.morph = group
        group.start()

    def compute_links(self):
        """Construye link_weights y link_pairs a partir de los enlaces de las notas."""
        self.link_weights = {}
        self.link_pairs = []
        seen_pairs = set()
        files = {}
        for i, node in enumerate(self.nodes):
            if node.path.suffix == '.md':
                files[i] = {node.path}
            elif node.path.is_dir():
                try:
                    notes = self.shell.vault.notes(node.path)
                except (OSError, ValueError):
                    notes = []
                files[i] = set(itertools.islice(notes, 200))
            else:
                files[i] = set()
        shown = {}
        for node in self.nodes:
            shown[node.path] = node
        for leaf in self.leaves:
            if getattr(leaf, 'path', None) is not None:
                shown[leaf.path] = leaf
        node_of = {node.path: i for i, node in enumerate(self.nodes)}
        vault = self.shell.vault
        for i, node_files in files.items():
            for f in node_files:
                try:
                    targets = vault.links(f)
                except (OSError, ValueError):
                    continue
                for t in targets:
                    j = node_of.get(t)
                    if j is not None and j != i:
                        key = (min(i, j), max(i, j))
                        self.link_weights[key] = self.link_weights.get(key, 0) + 1
                    if f in shown and t in shown:
                        wa = shown[f]
                        wb = shown[t]
                        if wa is not wb:
                            pair_id = (id(wa), id(wb))
                            if pair_id not in seen_pairs and (pair_id[1], pair_id[0]) not in seen_pairs:
                                seen_pairs.add(pair_id)
                                self.link_pairs.append((wa, wb))

    def select_widget(self, node):
        """Selecciona la nota del widget y le da el foco."""
        if node:
            self.select(node.path)
            node.setFocus()

    def focusNextPrevChild(self, next):
        """Empieza el tabulado en el mapa si ningún nodo tiene el foco."""
        map_nodes = [n for n in self.nodes if isinstance(n, MapNode)]
        if map_nodes and not any(n.hasFocus() for n in map_nodes):
            topmost = min(map_nodes, key=lambda n: n.geometry().y())
            self.select_widget(topmost)
            return True
        return super().focusNextPrevChild(next)


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
        self.search = QLineEdit(); self.search.setPlaceholderText('Nombre o contenido de notas…')
        self.search.setAccessibleName('Buscar en el explorador')
        self.search.setToolTip('Busca en nombres, rutas y contenido guardado de notas Markdown; incluye subcarpetas.')
        self.search.textChanged.connect(self.refresh); layout.addWidget(self.search)
        self.items = QListWidget(); self.items.setStyleSheet('QListWidget { border: none; background: transparent; }')
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.items.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.items.customContextMenuRequested.connect(self.context_menu)
        self.items.itemActivated.connect(self.activate); layout.addWidget(self.items)
        self.items.itemClicked.connect(self.single_click)
        tools = QHBoxLayout()
        tools.addWidget(button('Copiar', lambda: shell.files.copy(self.selected_paths())))
        tools.addWidget(button('Pegar', lambda: shell.files.paste(self.folder)))
        tools.addWidget(button('Importar carpeta', lambda: shell.files.import_folder(self.folder)))
        tools.addWidget(button('Importar notas', lambda: shell.files.import_files(self.folder)))
        layout.addLayout(tools)
        row = QHBoxLayout()
        row.addWidget(button('Nueva nota', self.new_note)); row.addWidget(button('Nueva carpeta', self.new_folder))
        row.addStretch(); row.addWidget(button('Abrir', lambda: self.activate(self.items.currentItem())))
        layout.addLayout(row)
        self.feedback = label('Ctrl+C copiar · Ctrl+V pegar · Ctrl+D duplicar', 'muted')
        self.feedback.setWordWrap(True); layout.addWidget(self.feedback)
        self.refresh()
        shell.files.changed.connect(self.refresh)
        shell.files.message.connect(self.feedback.setText)
        self.finished.connect(lambda: shell.files.changed.disconnect(self.refresh))
        for key, action in [('Alt+Up', self.go_up), ('F5', self.refresh), ('Ctrl+N', self.new_note),
                            ('Ctrl+Shift+N', self.new_folder), ('Ctrl+Alt+N', self.new_project),
                            ('Ctrl+W', self.reject), ('Ctrl+L', self.search.setFocus),
                            ('Ctrl+F', self.search.setFocus), ('Ctrl+R', self.refresh)]:
            shortcut = QShortcut(QKeySequence(key), self); shortcut.activated.connect(action)

    def single_click(self, item):
        if self.shell.accessibility.single_click and QApplication.keyboardModifiers() == Qt.KeyboardModifier.NoModifier:
            self.activate(item)

    def selected_paths(self):
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.items.selectedItems()]

    def context_menu(self, position):
        menu = self.shell.files.menu(self.items, self.selected_paths(), self.folder,
                                    open_path=self.open_path, create_note=self.new_note,
                                    create_folder=self.new_folder, create_project=self.new_project)
        menu.exec(self.items.viewport().mapToGlobal(position)); menu.deleteLater()
        self.refresh()

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
        self.open_path(path)

    def open_path(self, path):
        if path.is_dir():
            self.go(path)
        else:
            self.shell.navigate(self.folder); self.shell.activate(path); self.accept()

    def show_map(self):
        self.shell.navigate(self.folder); self.accept()

    def new_note(self):
        if self.shell.new_note(folder=self.folder):
            self.accept()
        else:
            self.refresh()

    def new_folder(self):
        path = self.shell.new_folder(folder=self.folder)
        self.go(path) if path else self.refresh()

    def _open_under(self, paths):
        return [p for p in self.panels if any(p == q or p.is_relative_to(q) for q in paths)]

    def rename_path(self, path):
        if self._open_under([path]):
            self.status.setText('Cierra primero la nota abierta para renombrarla.'); return
        current = path.stem if path.is_file() else path.name
        name, ok = QInputDialog.getText(self, 'Renombrar', 'Nuevo nombre:', text=current)
        if not ok or not name.strip() or name.strip() == current:
            return
        try:
            target, updated = self.vault.rename(path, name)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'No se pudo renombrar', str(error)); return
        self.surface.selection = []
        self.navigate(target if target.is_dir() and path == self.folder else self.folder if self.folder.exists() else target.parent)
        self.refresh_projects()
        self.status.setText(f'Renombrado a {target.name}' + (f' · enlaces actualizados en {len(updated)} notas' if updated else ''))

    def trash_paths(self, paths):
        if not paths:
            return
        if self._open_under(paths):
            self.status.setText('Cierra primero las notas abiertas.'); return
        names = ', '.join(p.name for p in paths[:4]) + ('…' if len(paths) > 4 else '')
        if QMessageBox.question(self, 'Mover a la papelera', f'¿Mover a la papelera {names}?\n'
                                'Puedes recuperarlos desde Crear › Papelera.') != QMessageBox.StandardButton.Yes:
            return
        moved = []
        for path in paths:
            try:
                self.vault.trash(path); moved.append(path.name)
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'No se pudo mover ' + path.name, str(error))
        if moved:
            self.surface.selection = []
            folder = self.folder
            while not folder.exists():
                folder = folder.parent
            self.navigate(folder); self.refresh_projects()
            self.status.setText('En la papelera: ' + ', '.join(moved))

    def new_project(self):
        if self.shell.new_project():
            self.accept()


class Desktop(QMainWindow):
    """Coordina mapa, notas y diálogos; Vault concentra el acceso a los archivos."""
    PAGE_SIZE = 8

    def __init__(self, root, kiosk=False, system_session=False, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings('PrOSperus', 'Desktop')
        self.accessibility = Accessibility.load(self.settings)
        self.vault = Vault(root)
        self.folder = self.vault.root
        self.kiosk = kiosk
        # Pantalla completa no equivale a controlar el sistema. Los controles
        # de sesión se habilitan únicamente en la imagen preparada para la VM.
        self.system_session = system_session and Path('/etc/prosperus-vm').is_file()
        self.panels = {}
        self.app_browser = None
        self.history = [self.folder]
        self.history_index = 0
        self.desktop_hidden = []
        self.page = 0
        self.colors = Palette()
        self.apps = ApplicationService(self)
        self.apps.failed.connect(lambda error: self.status.setText(error))
        self.apps.favorites_changed.connect(self.update_dock)
        self.apps.working_directory = str(self.folder)
        # Con Sway, las aplicaciones flotan sobre el mapa: pantalla completa o
        # Fibonacci, y cada proyecto es un espacio propio.
        self.windows = WindowManager(self, self.layout_options)
        self.windows.message.connect(lambda text: self.status.setText(text))
        self.app_windows = []
        self.windows.windows_changed.connect(self.set_app_windows)
        self.windows.project_step.connect(self.step_project)
        self.project_paths = []
        self.watcher = QFileSystemWatcher(self)
        self.watch_timer = QTimer(self)
        self.watch_timer.setSingleShot(True)
        self.watch_timer.setInterval(300)
        self.watch_timer.timeout.connect(self.files_changed)
        self.watcher.directoryChanged.connect(lambda: self.watch_timer.start())
        self.setWindowTitle('PrOSperus desktop')
        self.resize(1360, 850)
        self.setMinimumSize(860, 650)
        self.background = Wallpaper()
        self.viewport = QScrollArea(); self.viewport.setWidgetResizable(True)
        self.viewport.setWidget(self.background); self.setCentralWidget(self.viewport)
        layout = QVBoxLayout(self.background)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        layout.setContentsMargins(42, 26, 36, 18)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        icon = lambda kind: symbol_icon(kind, '#d4dbc8')
        self.create_menu = HoverMenuButton('Crear', icon('note-plus'), [
            ('Nueva nota', icon('note-plus'), self.new_note),
            ('Nueva carpeta', icon('folder-plus'), self.new_folder),
            ('Nuevo proyecto', icon('folder-plus'), self.new_project), None,
            ('Importar notas', icon('note'), lambda: self.files.import_files(self.folder)),
            ('Importar carpeta', icon('folder'), lambda: self.files.import_folder(self.folder)),
            ('Pegar', icon('note'), lambda: self.files.paste(self.folder)), None,
            ('Tus proyectos', icon('folders'), self.toggle_projects),
            ('Explorador', icon('search'), self.open_explorer),
            ('Papelera', icon('trash'), self.open_trash),
            ('Actualizar', icon('refresh'), self.refresh_projects)])
        heading.addWidget(self.create_menu, 0, Qt.AlignmentFlag.AlignTop)
        identity = QVBoxLayout(); identity.setSpacing(5)
        identity.addWidget(label('E S C R I T O R I O   D E   P R O Y E C T O S', 'eyebrow'))
        self.title = label('', 'title'); identity.addWidget(self.title)
        self.breadcrumb = label('', 'muted'); identity.addWidget(self.breadcrumb)
        heading.addLayout(identity, 1)
        actions = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Nombre o contenido…  Ctrl+L')
        self.search.setToolTip('Busca en nombres, rutas y contenido guardado de notas Markdown; incluye subcarpetas.')
        self.search.setAccessibleName('Buscar notas')
        self.search.textChanged.connect(self.search_changed); actions.addWidget(self.search); self.search.hide()
        heading.addLayout(actions)
        # Esquina derecha: brillo, volumen, wifi, bluetooth y notificaciones.
        self.quick = HoverMenuButton('Sistema', icon('sliders'), [])
        self.quick_panel = QuickSettings(self)
        quick_action = QWidgetAction(self.quick.menu); quick_action.setDefaultWidget(self.quick_panel)
        self.quick.menu.addAction(quick_action)
        self.quick.menu.aboutToShow.connect(self.quick_panel.refresh)
        self.quick.menu.setStyleSheet(f'QMenu {{ background: {self.colors.panel}; border: 1px solid {self.colors.border}; padding: 4px; }}')
        heading.addWidget(self.quick, 0, Qt.AlignmentFlag.AlignTop)
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
        self.status = label('Un clic selecciona · Doble clic abre · Clic derecho para más acciones', 'muted'); self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        footer.addWidget(label('PrOSperus · ' + __version__, 'muted'))
        layout.addLayout(footer)
        self.power_box = QWidget(); self.power_row = QHBoxLayout(self.power_box)
        layout.addWidget(self.power_box); self.power_box.hide()
        self.files = FileActions(self)
        self.controls = SessionControls(self)
        self.controls.message.connect(self.status.setText)
        self.keys = DesktopKeys(self)
        self.drawer = ProjectDrawer(self)
        self.edge = ProjectEdge(self)
        self.shortcuts = []
        self.shortcut('Escape', self.close_top_note)
        self.shortcut('Ctrl+L', lambda: self.open_applications('files'))
        self.shortcut('Ctrl+F', lambda: self.open_applications('files'))
        self.shortcut('Ctrl+O', self.open_first_note)
        self.shortcut('Ctrl+N', self.new_note)
        self.shortcut('Ctrl+Home', lambda: self.navigate(self.vault.root))
        self.shortcut('Ctrl+B', self.toggle_projects)
        self.shortcut('Ctrl+I', self.show_about)
        for key, action in [('Ctrl+Shift+N', self.new_folder), ('Ctrl+Alt+N', self.new_project),
                            ('Ctrl+Space', self.toggle_applications), ('Meta+E', self.open_explorer),
                            ('Meta+D', self.toggle_desktop), ('Meta+I', self.open_controls),
                            ('Alt+Up', self.go_up), ('Alt+Left', lambda: self.history_step(-1)),
                            ('Alt+Right', lambda: self.history_step(1)), ('Ctrl+W', self.close_top_note),
                            ('F1', self.show_help), ('F5', self.refresh_projects), ('Ctrl+R', self.refresh_projects),
                            ('Alt+F2', self.toggle_applications), ('Ctrl+Tab', self.next_note),
                            ('Ctrl+Shift+Tab', lambda: self.next_note(-1)),
                            ('F11', self.toggle_fullscreen)]:
            self.shortcut(key, action)
        self.refresh_projects()
        for index in range(9):
            self.shortcut(f'Ctrl+{index + 1}', lambda i=index: self.open_project_index(i))
        self.apply_accessibility()
        print('PROSPERUS_READY ' + __version__, flush=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_overlays()

    def position_overlays(self):
        if hasattr(self, 'drawer'):
            self.drawer.setGeometry(0, 0, min(round(370 * self.accessibility.text_scale / 100), self.width() - 100), self.background.height())
            self.edge.setGeometry(0, self.background.height() // 2 - 45, 25, 90)
            self.drawer.raise_()

    def shortcut(self, key, callback):
        item = QShortcut(QKeySequence(key), self); item.activated.connect(callback); self.shortcuts.append(item)

    def apply_appearance(self):
        self.colors = self.accessibility.palette(palette_for(self.vault, self.folder))
        self.setStyleSheet(self.accessibility.css(self.colors))
        self.background.palette = self.colors
        self.background.wallpaper = None if self.accessibility.high_contrast else wallpaper_for(self.vault, self.folder)
        self.background.update(); self.surface.update()
        # Con dos pantallas, la que no tiene el mapa muestra el fondo del proyecto (no un color liso).
        self.windows.set_wallpaper(self.background.wallpaper, self.colors.base)

    def apply_accessibility(self):
        self.apply_appearance()
        self.dock_scroll.setFixedHeight(max(62, round(62 * self.accessibility.text_scale / 100),
                                            80 if self.accessibility.large_buttons else 62))
        for panel in self.panels.values():
            panel.colors = self.accessibility.palette(palette_for(self.vault, panel.path.parent))
            panel.wallpaper = None if self.accessibility.high_contrast else wallpaper_for(self.vault, panel.path)
            panel.setStyleSheet(self.accessibility.css(panel.colors)); panel.update()
        self.drawer.refresh()
        self.update_dock()
        self.position_overlays()

    def next_note(self, direction=1):
        panels = [p for p in self.panels.values() if p.project == self.folder and not p.minimized]
        if not panels:
            return
        focus = QApplication.focusWidget()
        index = next((i for i, p in enumerate(panels) if focus == p or (focus and p.isAncestorOf(focus))),
                     -1 if direction == 1 else 0)
        panels[(index + direction) % len(panels)].restore()

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
        dialog = Explorer(self); dialog.exec(); dialog.deleteLater()

    def open_applications(self, mode='apps'):
        if self.app_browser is not None:
            self.app_browser.set_mode(mode)
        else:
            self.app_browser = ApplicationBrowser(self, mode)
            self.app_browser.finished.connect(self.applications_closed)
            shortcut = QShortcut(QKeySequence('Ctrl+Space'), self.app_browser)
            shortcut.activated.connect(self.app_browser.reject)
        self.app_browser.show(); self.app_browser.raise_(); self.app_browser.activateWindow()
        self.app_browser.search.setFocus()

    def applications_closed(self):
        self.app_browser.deleteLater(); self.app_browser = None
        self.activateWindow(); self.surface.setFocus()

    def toggle_applications(self):
        self.app_browser.reject() if self.app_browser is not None else self.open_applications()

    def open_controls(self):
        dialog = ControlsDialog(self); dialog.exec(); dialog.deleteLater()

    def open_layout_settings(self):
        dialog = LayoutDialog(self); dialog.exec(); dialog.deleteLater()

    def open_display_settings(self):
        from .display_settings import DisplayDialog
        dialog = DisplayDialog(self); dialog.exec(); dialog.deleteLater()

    def open_accessibility(self):
        dialog = AccessibilityDialog(self); dialog.exec(); dialog.deleteLater()

    def offer_drivers(self):
        """Primer arranque: ofrecer controladores si la gráfica lo necesita (una vez por gráfica)."""
        from .driver_assistant import DriverAssistant, detect_gpus, needs_attention, plan_for, secure_boot_enabled
        try:
            plans = [plan_for(gpu, secure_boot_enabled()) for gpu in detect_gpus()]
        except OSError:
            return
        key = 'drivers/asked/' + '-'.join(f'{p.gpu.vendor}:{p.gpu.device:x}' for p in plans)
        if not needs_attention(plans) or self.settings.value(key, False, type=bool):
            return
        self.settings.setValue(key, True); self.settings.sync()
        dialog = DriverAssistant(self, plans); dialog.exec(); dialog.deleteLater()

    def open_hardware(self):
        dialog = HardwareDialog(self); dialog.exec(); dialog.deleteLater()

    def show_help(self):
        dialog = QDialog(self); dialog.setWindowTitle('Atajos y manejo del escritorio'); dialog.resize(640, 570)
        layout = QVBoxLayout(dialog)
        text = QTextBrowser(); text.setMarkdown(SHORTCUT_HELP); layout.addWidget(text)
        layout.addWidget(button('Cerrar', dialog.accept))
        dialog.exec(); dialog.deleteLater()

    def show_about(self):
        dialog = QDialog(self); dialog.setWindowTitle('Acerca de PrOSperus'); dialog.resize(420, 360)
        layout = QVBoxLayout(dialog)
        info = QTextBrowser(); info.setOpenExternalLinks(True)
        info.setMarkdown(f'''
# PrOSperus desktop

**Versión:** {__version__}

**Autor:** Nicolás (harasmeant)

**Licencia:** GNU General Public License v3 exclusivamente (GPL-3.0-only)

**Descripción:** Escritorio orientado a proyectos inspirado en el prototipo de Obsidian.

## Información del sistema

- **Sistema operativo:** {sys.platform}
- **Python:** {sys.version.split()[0]}
- **Qt:** {PySide6.__version__}

## Enlaces

- Repositorio: https://github.com/harasmeant/PrOSperus-desktop
- Issues: https://github.com/harasmeant/PrOSperus-desktop/issues

''')
        layout.addWidget(info)
        layout.addWidget(button('Cerrar', dialog.accept))
        dialog.exec(); dialog.deleteLater()

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() and not self.kiosk else self.showFullScreen()

    def layout_options(self):
        # Mismo perfil guardado en «Distribución» para la pantalla estándar.
        screen = QApplication.primaryScreen()
        size = screen.availableGeometry() if screen else None
        profile = screen_profile(size.width(), size.height()) if size else 'standard'
        prefix = 'layouts/profiles/' + profile + '/'
        try:
            options = LayoutOptions(str(self.settings.value(prefix + 'mode', 'spiral')),
                                    *[int(self.settings.value(prefix + key, default))
                                      for key, default in [('gap', 12), ('ratio', 50), ('max_width', 0)]])
            options.validate(); return options
        except (TypeError, ValueError):
            return LayoutOptions()

    def toggle_app_mode(self):
        self.windows.set_mode('fullscreen' if self.windows.mode == 'fibonacci' else 'fibonacci')
        if self.windows.mode == 'fibonacci':
            self.arrange_notes()
        self.update_dock()

    def set_app_windows(self, windows):
        if windows != self.app_windows:
            self.app_windows = windows; self.update_dock()

    def toggle_desktop(self):
        self.windows.show_desktop()
        visible = [panel.path for panel in self.panels.values() if panel.isVisible()]
        if visible:
            self.desktop_hidden = visible
            for path in visible:
                self.panels[path].minimize()
            self.surface.setFocus()
        else:
            for path in self.desktop_hidden:
                if path in self.panels and self.panels[path].project == self.folder:
                    self.panels[path].restore()
            self.desktop_hidden = []

    def file_context(self, target):
        if target == self.surface or isinstance(target, MapNode):
            return self.folder, list(self.surface.selection), self.surface.select_all, self.go_up
        window = target.window()
        if isinstance(window, Explorer) and (target == window.items or window.items.isAncestorOf(target)):
            return window.folder, window.selected_paths(), window.items.selectAll, window.go_up
        return None

    def history_step(self, direction):
        index = self.history_index + direction
        if 0 <= index < len(self.history):
            if self.navigate(self.history[index], record=False):
                self.history_index = index

    def navigate(self, folder, record=True):
        try:
            folder = self.vault.checked(folder)
            if not folder.is_dir():
                raise ValueError('Selecciona una carpeta.')
            if record and folder != self.folder:
                self.history = self.history[:self.history_index + 1] + [folder]
                self.history_index = len(self.history) - 1
            self.folder = folder; self.page = 0
            self.apps.working_directory = str(folder)
            parts = folder.relative_to(self.vault.root).parts
            self.windows.switch_workspace(parts[0] if parts else 'General')
            self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
            self.apply_appearance(); self.render()
            for panel in self.panels.values():
                panel.setVisible(panel.project == self.folder and not panel.minimized)
            self.update_dock()
            if self.drawer.isVisible():
                self.drawer.refresh()
            self.surface.setFocus()
            return True
        except (OSError, ValueError) as error:
            self.status.setText(str(error))

    def go_up(self):
        if self.folder != self.vault.root:
            self.navigate(self.folder.parent)

    def search_changed(self):
        self.page = 0; self.render()

    def change_page(self, direction):
        page = self.page
        self.page += direction; self.render()
        if self.page != page:
            self.surface.slide_page(direction)

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
        self.surface.selection = []
        for path in entries[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]:
            item = MapNode(self.surface, path)
            item.title = path.name if path.is_dir() or path.suffix.lower() != '.md' else path.stem
            item.setText(item.title)
            item.subtitle = ('Carpeta · Doble clic' if path.is_dir() else 'Nota · Doble clic'
                             if path.suffix.lower() == '.md' else 'Archivo · Abrir con su aplicación')
            item.show(); self.surface.nodes.append(item)
        self.surface.center.title = self.title.text()
        self.surface.center.subtitle = f'{len(entries)} archivos y carpetas' if entries else 'Crea tu primera nota'
        self.page_label.setText(f'{self.page + 1} / {max(1, math.ceil(len(entries) / self.PAGE_SIZE))}')
        self.previous.setEnabled(self.page > 0); self.next.setEnabled((self.page + 1) * self.PAGE_SIZE < len(entries))
        self.surface.build_leaves(); self.surface.arrange()
        for panel in self.panels.values():
            if panel.isVisible():
                panel.raise_()

        watch_strings = {str(self.folder)}
        for node in self.surface.nodes:
            node_path = getattr(node, "path", None)
            if node_path is not None and node_path.is_dir():
                watch_strings.add(str(node_path))
        watch_strings.add(str(self.vault.root))

        for directory in list(self.watcher.directories()):
            if directory not in watch_strings:
                self.watcher.removePath(directory)
        for path in watch_strings:
            if path not in self.watcher.directories() and os.path.exists(path):
                self.watcher.addPath(path)

    def step_project(self, direction):
        if not self.project_paths:
            return
        index = next((i for i, p in enumerate(self.project_paths) if self.folder.is_relative_to(p)), -1 if direction > 0 else 0)
        new_index = (index + direction) % len(self.project_paths)
        path = self.project_paths[new_index]
        self.navigate(path)
        self.status.setText('Proyecto: ' + path.name)

    def files_changed(self):
        if not self.vault.root.is_dir():
            return
        if not self.folder.is_dir():
            # La carpeta abierta se borró desde fuera: volver a la raíz.
            self.navigate(self.vault.root); return
        # Un fondo nuevo en la carpeta cambia también la paleta.
        self.apply_appearance(); self.refresh_projects()
        self.render()

    def activate(self, path):
        if path.is_dir():
            self.navigate(path)
        elif path.suffix.lower() == '.md':
            self.open_note(path)
        else:
            self.status.setText('Abriendo ' + path.name + '…'); self.apps.run('open', str(path))

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
            self.place_note(panel)
            if edit and panel.pages.currentWidget() != panel.editor:
                panel.toggle_edit(); panel.editor.moveCursor(QTextCursor.MoveOperation.End)
            self.status.setText(str(path.relative_to(self.vault.root)))
        except (OSError, ValueError, UnicodeError) as error:
            self.status.setText(str(error))

    def place_note(self, panel):
        """Las notas siguen el modo del dock: Fibonacci las reparte, Pantalla completa amplía la nueva."""
        if self.windows.mode == 'fullscreen':
            panel.toggle_maximized(maximized=True)
        else:
            self.arrange_notes()

    def arrange_notes(self):
        panels = [p for p in self.panels.values() if p.project == self.folder and p.isVisible() and not p.minimized]
        if not panels:
            return
        area = self.surface.rect()
        try:
            boxes = arrange(Rect(0, 0, area.width(), area.height()), len(panels), self.layout_options(),
                            (max(p.minimumWidth() for p in panels), max(p.minimumHeight() for p in panels)))
        except ValueError as error:
            # Sin espacio para todas: se deja la posición que tenían.
            self.status.setText(str(error)); return
        for panel, box in zip(panels, boxes):
            panel.normal_geometry = None
            panel.setGeometry(box.x, box.y, box.width, box.height)

    def new_note(self, checked=False, folder=None):
        place = ask_place(self, self.vault, 'Nueva nota', folder or self.folder)
        if place:
            name, folder = place
            try:
                path = self.vault.create_note(folder, name)
                self.navigate(folder); self.open_note(path, edit=True); self.refresh_projects()
                return path
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'No se pudo crear la nota', str(error))

    def new_folder(self, checked=False, folder=None):
        place = ask_place(self, self.vault, 'Nueva carpeta', folder or self.folder)
        if place:
            name, folder = place
            try:
                path = self.vault.create_folder(folder, name)
                self.navigate(path); self.refresh_projects()
                return path
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'No se pudo crear la carpeta', str(error))

    def move_to(self, paths, destination=None):
        """Mueve notas o carpetas a otro proyecto; las notas abiertas deben cerrarse antes."""
        if not paths:
            self.status.setText('Selecciona una carpeta o una nota para mover.'); return
        # Un panel abierto guarda en su ruta: moverlo debajo perdería sus cambios.
        busy = [p for p in self.panels if any(p == q or p.is_relative_to(q) for q in paths)]
        if busy:
            self.status.setText('Cierra primero las notas abiertas: ' + ', '.join(p.stem for p in busy)); return
        place = (None, destination) if destination else ask_place(self, self.vault, 'Mover a…', self.folder, ask_name=False)
        if not place:
            return
        moved = []
        for path in paths:
            try:
                moved.append(self.vault.move(path, place[1]).name)
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'No se pudo mover ' + path.name, str(error))
        if moved:
            self.surface.selection = []
            self.navigate(self.folder); self.refresh_projects()
            self.status.setText('Movido a ' + place[1].name + ': ' + ', '.join(moved))

    def open_trash(self):
        """Papelera: lo borrado con Supr, con la carpeta de la que salió; Recuperar lo devuelve."""
        dialog = QDialog(self); dialog.setWindowTitle('Papelera'); dialog.resize(560, 440)
        layout = QVBoxLayout(dialog); layout.setContentsMargins(22, 20, 22, 20); layout.setSpacing(12)
        layout.addWidget(label('PAPELERA', 'section'))
        layout.addWidget(label('Lo que mueves a la papelera se guarda aquí. Recupéralo a su carpeta cuando quieras.', 'muted'))
        items = QListWidget(); items.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(items, 1)
        empty = label('La papelera está vacía.', 'muted'); layout.addWidget(empty)

        def fill():
            items.clear()
            for path, origin in self.vault.trashed():
                where = str(Path(origin).parent) if origin else ''
                text = (path.stem if path.is_file() else path.name) + '   ·   ' + ('en ' + where if where not in ('', '.') else 'en Tus proyectos')
                item = QListWidgetItem(symbol_icon('folder' if path.is_dir() else 'note', self.colors.accent), text)
                item.setData(Qt.ItemDataRole.UserRole, path.name); items.addItem(item)
            empty.setVisible(items.count() == 0)
            if items.count():
                items.setCurrentRow(0)

        def restore():
            restored = []
            for item in items.selectedItems():
                try:
                    restored.append(self.vault.restore(item.data(Qt.ItemDataRole.UserRole)))
                except (OSError, ValueError) as error:
                    QMessageBox.warning(dialog, 'No se pudo recuperar', str(error))
            if restored:
                self.navigate(self.folder); self.refresh_projects()
                self.status.setText('Recuperado: ' + ', '.join(p.name for p in restored))
            fill()

        row = QHBoxLayout(); row.addStretch(1)
        row.addWidget(button('Recuperar', restore)); row.addWidget(button('Cerrar', dialog.accept))
        layout.addLayout(row)
        items.itemActivated.connect(lambda _: restore())
        fill(); dialog.exec(); dialog.deleteLater()

    def new_project(self):
        name, ok = QInputDialog.getText(self, 'Nuevo proyecto', 'Nombre del proyecto:')
        if ok:
            try:
                path = self.vault.create_folder(self.vault.root, name)
                self.navigate(path); self.refresh_projects()
                self.drawer.hide()
                self.status.setText('Proyecto creado. Añade notas o pega carpetas con Ctrl+V.')
                return path
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'No se pudo crear el proyecto', str(error))

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
        focused = QApplication.focusWidget()
        for panel in visible:
            if focused == panel or (focused is not None and panel.isAncestorOf(focused)):
                panel.close_note(); return
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
        add_access(button('Aplicaciones', lambda: self.open_applications()))
        mode = button('Fibonacci' if self.windows.mode == 'fibonacci' else 'Pantalla completa', self.toggle_app_mode)
        mode.setToolTip('Cómo se abren notas y aplicaciones: Fibonacci las reparte, Pantalla completa ocupa todo. Pulsa para cambiar.')
        add_access(mode)
        if self.windows.available:
            for window in self.app_windows:
                item = button(window['name'], lambda checked=False, w=window: self.windows.toggle(w['id'], w['hidden']))
                item.setIcon(symbol_icon('window', self.colors.accent))
                item.setObjectName('minimized' if window['hidden'] else 'openNote')
                item.setToolTip(('Recuperar: ' if window['hidden'] else 'Enfocar o minimizar: ') + window['name'])
                add_access(item)
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
        if self.files.busy:
            self.status.setText('Espera a que termine la copia antes de apagar.'); return
        if not all(panel.can_close() for panel in list(self.panels.values())):
            return
        check = subprocess.run(['systemd-detect-virt', '--vm', '--quiet'], check=False)
        if check.returncode:
            self.status.setText('Estos controles solo están disponibles en la VM PrOSperus.'); return
        result = subprocess.run(['systemctl', action], capture_output=True, text=True, timeout=15)
        if result.returncode:
            self.status.setText(result.stderr.strip() or 'No se pudo completar la acción.')

    def closeEvent(self, event):
        if self.files.busy:
            event.ignore(); self.status.setText('Espera a que termine la copia antes de cerrar.')
        elif self.kiosk:
            event.ignore(); self.status.setText('Usa los controles de sesión para apagar.')
        elif all(panel.can_close() for panel in list(self.panels.values())):
            event.accept()
        else:
            event.ignore()


def main():
    # Mantener el punto de entrada pequeño permite usar la misma interfaz
    # como aplicación Fedora, sesión Live y captura de pruebas sin pantalla.
    parser = argparse.ArgumentParser(description='PrOSperus desktop — escritorio de proyectos')
    parser.add_argument('--root', type=Path, default=Path('/usr/share/prosperus/demo'))
    parser.add_argument('--kiosk', action='store_true')
    parser.add_argument('--system-session', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1]); app.setApplicationName('PrOSperus desktop')
    app.setDesktopFileName('org.prosperus.Desktop')
    app.setStyleSheet(STYLE)
    try:
        desktop = Desktop(args.root, args.kiosk, args.system_session)
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + '\n')
    # Bajo Sway el escritorio es la ventana de mosaico y ya ocupa la pantalla;
    # en pantalla completa taparía las aplicaciones flotantes.
    desktop.showFullScreen() if args.kiosk and not os.environ.get('SWAYSOCK') else desktop.show()
    desktop.windows.start()
    if desktop.system_session:
        QTimer.singleShot(1500, desktop.offer_drivers)
    if args.screenshot:
        def capture():
            desktop.grab().save(str(args.screenshot)); app.quit()
        QTimer.singleShot(500, capture)
    sys.exit(app.exec())
