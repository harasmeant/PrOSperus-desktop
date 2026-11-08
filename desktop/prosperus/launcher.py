"""Asynchronous GIO launcher, with explicitly pinned global favourites."""
# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
import sys

from PySide6.QtCore import QEvent, QObject, QProcess, QSettings, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QButtonGroup, QDialog, QPushButton, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QVBoxLayout

from .distro import current as current_distro
from .model import searchable


def use_icon_theme():
    """En Sway Qt no tiene tema de iconos (solo hicolor): Papirus oscuro si está instalado
    (imagen PrOSperus); si no, Adwaita con el clásico de respaldo."""
    if QIcon.themeName() in ('', 'hicolor'):
        papirus = any((Path(base) / 'Papirus-Dark').is_dir() for base in QIcon.themeSearchPaths())
        QIcon.setThemeName('Papirus-Dark' if papirus else 'Adwaita')
        QIcon.setFallbackThemeName('Adwaita' if papirus else 'AdwaitaLegacy')


def app_item(app, favorites, colors):
    """Return a QListWidgetItem for an application dict in an icon grid."""
    from .appearance import symbol_icon
    item = QListWidgetItem()
    icon_path = app.get('icon', '')
    if icon_path.startswith('/') and Path(icon_path).is_file():
        icon = QIcon(icon_path)
    elif app.get('icon'):
        icon = QIcon.fromTheme(app['icon'])
    else:
        icon = symbol_icon('apps', colors.accent)
    if icon.isNull():
        icon = symbol_icon('apps', colors.accent)
    item.setIcon(icon)
    item.setText(f"{'★  ' if app['id'] in favorites else ''}{app['name']}")
    item.setToolTip(app.get('description') or app['name'])
    item.setData(Qt.ItemDataRole.UserRole, dict(app, kind='app'))
    item.setSizeHint(QSize(120, 104))
    item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    return item


class ApplicationService(QObject):
    completed = Signal(str, object)
    failed = Signal(str)
    favorites_changed = Signal()

    # Carga favoritos globales y prepara lanzador
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings if settings is not None else QSettings('PrOSperus', 'Desktop')
        try:
            data = json.loads(self.settings.value('favorite-apps', '[]'))
            self.favorites = [a for a in data if isinstance(a, dict) and isinstance(a.get('id'), str) and isinstance(a.get('name'), str)] if isinstance(data, list) else []
        except (TypeError, ValueError):
            self.favorites = []
        self.catalogue = []
        self.action = ''
        # Carpeta del proyecto actual: las aplicaciones heredan este directorio.
        self.working_directory = ''
        self.process = QProcess(self)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)

    # Ejecuta aplicaciones con favoritos globales
    def run(self, action, *args):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.failed.emit('Hay una operación de aplicaciones en curso.'); return
        self.action = action
        arguments = [str(Path(__file__).with_name('applications.py')), action]
        arguments += [str(a) for a in args if a is not None]
        self.process.setWorkingDirectory(self.working_directory)
        self.process.start(sys.executable, arguments)

    def process_error(self, error):
        self.failed.emit('No se pudo ejecutar el servicio de aplicaciones: ' + self.process.errorString())

    # Procesar resultados de comandos ejecutados
    def finished(self, code, status):
        error = bytes(self.process.readAllStandardError()).decode('utf-8', errors='replace').strip()
        output = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        if code or status != QProcess.ExitStatus.NormalExit:
            self.failed.emit(error or 'No se pudo completar la operación.'); return
        try:
            data = json.loads(output)
            if self.action == 'list':
                if not isinstance(data, list):
                    raise ValueError('Catálogo no válido.')
                self.catalogue = data
            self.completed.emit(self.action, data)
        except (ValueError, TypeError) as error:
            self.failed.emit('No se pudo leer la respuesta: ' + str(error))

    # Alternar aplicaciones en favoritos
    def toggle_favorite(self, app):
        pinned = any(a['id'] == app['id'] for a in self.favorites)
        next_favorites = [a for a in self.favorites if a['id'] != app['id']]
        if not pinned:
            next_favorites.append({'id': app['id'], 'name': app['name']})
        self.settings.setValue('favorite-apps', json.dumps(next_favorites, ensure_ascii=False))
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            self.failed.emit('No se pudieron guardar las aplicaciones favoritas.'); return
        self.favorites = next_favorites
        self.favorites_changed.emit()


class ApplicationBrowser(QDialog):
    # Permite buscar aplicaciones y archivos en el sistema
    def __init__(self, shell, mode='apps'):
        super().__init__(shell)
        # Imported here to keep the shell/launcher dependency one-way at load time.
        from .shell import button
        self.shell = shell
        self.service = shell.apps
        self.mode = mode
        use_icon_theme()
        self.setWindowTitle('Buscar')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.resize(720, 540)

        layout = QVBoxLayout(self)

        # Mode selection row
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.btn_files = QPushButton('Archivos')
        self.btn_apps = QPushButton('Programas')
        self.btn_all = QPushButton('Todo')
        for btn in [self.btn_files, self.btn_apps, self.btn_all]:
            self.mode_group.addButton(btn)
            btn.setCheckable(True)
            mode_layout.addWidget(btn)
        # Sin marco no hay botón de cerrar de la ventana: uno propio (también Esc o Super).
        mode_layout.addStretch()
        # Icono dibujado: la letra ✕ cae en otra fuente y queda descentrada en el círculo.
        from .appearance import symbol_icon
        self.close_button = QPushButton(symbol_icon('close', self.shell.colors.text), '')
        self.close_button.setIconSize(QSize(20, 20))
        self.close_button.setObjectName('launcherClose')
        self.close_button.setToolTip('Cerrar (Esc o Super)')
        self.close_button.setAccessibleName('Cerrar')
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setFixedSize(36, 36)
        self.close_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.close_button.clicked.connect(self.reject)
        mode_layout.addWidget(self.close_button)
        self.mode_group.buttonToggled.connect(self.on_mode_changed)
        layout.addLayout(mode_layout)

        # Title row
        self.title = QLabel('Buscar')
        self.title.setObjectName('launcherTitle')
        layout.addWidget(self.title)

        # Search row
        self.search = QLineEdit()
        self.search.setObjectName('launcherSearch')
        self.search.setMinimumHeight(44)
        self.search.setPlaceholderText('Nombre, descripción o palabra clave…')
        self.search.textChanged.connect(self.render)
        layout.addWidget(self.search)

        # Grid list
        self.list = QListWidget()
        self.list.setViewMode(QListView.ViewMode.IconMode)
        self.list.setIconSize(QSize(48, 48))
        self.list.setGridSize(QSize(132, 116))
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setMovement(QListView.Movement.Static)
        self.list.setWordWrap(True)
        self.list.setUniformItemSizes(True)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.list.setSpacing(8)
        self.list.setObjectName('launcherGrid')
        self.list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.list.itemActivated.connect(lambda _: self.launch())
        self.list.currentItemChanged.connect(self.selection_changed)
        layout.addWidget(self.list)

        # Status label
        self.status = QLabel('')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        # Button row
        row = QHBoxLayout()
        row.addWidget(button('Actualizar lista', self.refresh))
        row.addStretch()
        self.favorite = button('Fijar', self.toggle_favorite)
        row.addWidget(self.favorite)
        self.open = button('Abrir', self.launch)
        row.addWidget(self.open)
        if self.shell.system_session:
            row.addWidget(button('Cerrar sesión', lambda: (self.accept(), self.shell.ask_power('logout'))))
            row.addWidget(button('Reiniciar', lambda: (self.accept(), self.shell.ask_power('reboot'))))
            row.addWidget(button('Apagar', lambda: (self.accept(), self.shell.ask_power('poweroff'))))
        layout.addLayout(row)

        # Service connections
        self.service.completed.connect(self.completed)
        self.service.failed.connect(self.report_error)
        self.service.favorites_changed.connect(self.render)
        self.finished.connect(self.disconnect_service)

        # Apply stylesheet using shell palette
        self.setStyleSheet(f"""
    QDialog {{
        background-color: {self.shell.colors.panel};
        border: 1px solid {self.shell.colors.border};
        border-radius: 14px;
    }}
    #launcherClose {{
        border-radius: 18px;
        font-size: 16px;
        padding: 0;
    }}
    #launcherClose:hover {{
        background-color: {self.shell.colors.hover};
        border-color: {self.shell.colors.accent};
    }}
    #launcherTitle {{
        font-size: 20px;
        font-weight: bold;
        color: {self.shell.colors.text};
    }}
    #launcherSearch {{
        background-color: {self.shell.colors.card};
        border: 1px solid {self.shell.colors.border};
        border-radius: 12px;
        padding: 10px 16px;
        min-height: 24px;
        font-size: 15px;
    }}
    #launcherSearch:focus {{
        border-color: {self.shell.colors.accent};
    }}
    #launcherGrid {{
        background-color: transparent;
        border: none;
    }}
    #launcherGrid::item {{
        background-color: {self.shell.colors.card};
        border: 1px solid {self.shell.colors.border};
        border-radius: 14px;
        padding: 10px 6px 6px 6px;
        margin: 4px;
        color: {self.shell.colors.text};
    }}
    #launcherGrid::item:hover {{
        background-color: {self.shell.colors.hover};
    }}
    #launcherGrid::item:selected {{
        border: 2px solid {self.shell.colors.accent};
        background-color: {self.shell.colors.hover};
    }}
    """)

        # Initialize plocate process
        self.locate = None

        # Focus search and install event filter
        self.search.setFocus()
        self.search.installEventFilter(self)

        # Set initial mode
        self.set_mode(self.mode)
        self.render()
        if not self.service.catalogue:
            self.refresh()

    # Detener señales del servicio para evitar llamadas adicionales
    def disconnect_service(self):
        for signal, slot in ((self.service.completed, self.completed),
                             (self.service.failed, self.report_error),
                             (self.service.favorites_changed, self.render)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass  # ya desconectada en un cierre anterior

    # Mostrar error al faltar PyGObject
    def report_error(self, message):
        if 'gi' in message and 'module' in message:
            message = ('Falta el componente de aplicaciones (PyGObject). Instálalo y pulsa Actualizar lista: '
                       + current_distro().shell_install(current_distro().gobject))
        self.status.setText(message)

    def refresh(self):
        self.status.setText('Buscando aplicaciones instaladas…'); self.service.run('list')

    # Procesa acciones completadas para renderizar o lanzar
    def completed(self, action, data):
        if action == 'list':
            self.render()
        elif action == 'launch':
            self.accept()

    # Mostrar resultados de búsqueda en aplicaciones y proyectos
    def render(self):
        selected = self.selected()
        selected_id = selected.get('id') if selected else None
        self.list.clear()
        favorites = {a['id'] for a in self.service.favorites}
        terms = searchable(self.search.text()).split()
        text = self.search.text().strip()

        if self.mode == 'apps':
            apps = [app for app in self.service.catalogue if all(t in searchable(' '.join([app['name'], app.get('description', ''), *app.get('keywords', [])])) for t in terms)]
            from .appearance import symbol_icon
            for app in sorted(apps, key=lambda a: (a['id'] not in favorites, searchable(a['name']))):
                item = app_item(app, favorites, self.shell.colors)
                self.list.addItem(item)
                if app['id'] == selected_id:
                    self.list.setCurrentItem(item)
            if self.list.currentRow() < 0 and self.list.count():
                self.list.setCurrentRow(0)
            self.status.setText(f'{len(apps)} aplicaciones · Favoritas globales')
        elif self.mode == 'files':
            if not text:
                self.status.setText('Escribe para buscar en tus proyectos.')
                return
            try:
                paths = self.shell.vault.search(text, self.shell.vault.root)[:200]
            except (OSError, ValueError) as e:
                self.status.setText(str(e))
                return
            from .appearance import symbol_icon
            for path in paths:
                is_dir = path.is_dir()
                item_text = path.name if is_dir else path.stem
                icon = symbol_icon('folder' if is_dir else 'note', self.shell.colors.accent)
                item = QListWidgetItem(item_text)
                item.setIcon(icon)
                item.setToolTip(str(path))
                item.setData(Qt.ItemDataRole.UserRole, {'kind': 'path', 'path': path})
                self.list.addItem(item)
            self.status.setText(f'{len(paths)} resultados en proyectos')
        elif self.mode == 'all':
            if len(text) < 2:
                self.status.setText('Escribe al menos 2 caracteres para buscar.')
                return
            # Apps
            apps = [app for app in self.service.catalogue if all(t in searchable(' '.join([app['name'], app.get('description', ''), *app.get('keywords', [])])) for t in terms)]
            from .appearance import symbol_icon
            for app in sorted(apps, key=lambda a: (a['id'] not in favorites, searchable(a['name']))):
                item = app_item(app, favorites, self.shell.colors)
                self.list.addItem(item)
            # Vault paths
            try:
                paths = self.shell.vault.search(text, self.shell.vault.root)[:200]
            except (OSError, ValueError) as e:
                self.status.setText(str(e))
                return
            shown_paths = {p['path'] for p in [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())] if p.get('kind') == 'path'}
            for path in paths:
                if path in shown_paths:
                    continue
                is_dir = path.is_dir()
                item_text = path.name if is_dir else path.stem
                icon = symbol_icon('folder' if is_dir else 'note', self.shell.colors.accent)
                item = QListWidgetItem(item_text)
                item.setIcon(icon)
                item.setToolTip(str(path))
                item.setData(Qt.ItemDataRole.UserRole, {'kind': 'path', 'path': path})
                self.list.addItem(item)
            # System files via plocate
            if self.locate is not None:
                self.locate.kill()
                self.locate = None
            self.locate = QProcess(self)
            self.locate.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
            self.locate.finished.connect(lambda code, status, proc=self.locate: self.handle_locate_finished(proc, code, status))
            self.locate.errorOccurred.connect(lambda error, proc=self.locate: self.handle_locate_error(proc, error))
            self.locate.start('plocate', ['-i', '-l', '60', text.strip()])
            self.status.setText('Buscando en el sistema…')
        self.selection_changed()

    def selected(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # Actualiza botones según app seleccionada
    def selection_changed(self, *args):
        app = self.selected()
        self.open.setEnabled(app is not None)
        self.favorite.setEnabled(app is not None and app.get('kind') == 'app')
        if app and app.get('kind') == 'app':
            self.favorite.setText('Desfijar' if any(a['id'] == app['id'] for a in self.service.favorites) else 'Fijar')
        else:
            self.favorite.setText('Fijar')

    # Alternar favorito global de la app seleccionada
    def toggle_favorite(self):
        app = self.selected()
        if app:
            self.service.toggle_favorite(app)

    # Abre aplicaciones y rutas seleccionadas
    def launch(self):
        app = self.selected()
        if not app:
            return
        kind = app.get('kind')
        if kind == 'app':
            self.status.setText('Abriendo ' + app['name'] + '…')
            self.service.run('launch', app['id'])
        elif kind == 'path':
            self.shell.activate(app['path'])
            self.accept()
        elif kind == 'system':
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(app['path'])))
            self.accept()

    # Intro en la cuadrícula ya abre por itemActivated; el diálogo además pulsaba un botón
    # por defecto y el segundo intento salía como «operación en curso».
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.focusWidget() is not self.list:
                self.launch()
            return
        super().keyPressEvent(event)

    # Enfoca lista de favoritos con flecha abajo
    def eventFilter(self, obj, event):
        if obj is self.search and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Down:
            self.list.setFocus()
            return True
        return super().eventFilter(obj, event)

    # Actualiza el modo y refresca la vista
    def on_mode_changed(self, btn, checked):
        if checked:
            if btn == self.btn_files:
                self.mode = 'files'
            elif btn == self.btn_apps:
                self.mode = 'apps'
            elif btn == self.btn_all:
                self.mode = 'all'
            self.set_mode(self.mode)
            self.render()

    # Permite cambiar el modo de búsqueda entre archivos apps y todos
    def set_mode(self, mode):
        placeholders = {
            'files': 'Carpetas y notas de tus proyectos…',
            'apps': 'Nombre, descripción o palabra clave…',
            'all': 'Programas, notas y archivos de todo el ordenador…'
        }
        self.search.setPlaceholderText(placeholders.get(mode, ''))
        # Update button states
        self.btn_files.setChecked(mode == 'files')
        self.btn_apps.setChecked(mode == 'apps')
        self.btn_all.setChecked(mode == 'all')

    # Añade rutas del sistema no mostradas previamente
    def handle_locate_finished(self, proc, exitCode, exitStatus):
        if proc != self.locate:
            return
        stdout = proc.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        paths = [Path(line.strip()) for line in stdout.splitlines() if line.strip()]
        # Filter out already shown vault paths
        existing = {item.data(Qt.ItemDataRole.UserRole)['path'] for item in [self.list.item(i) for i in range(self.list.count())] if item.data(Qt.ItemDataRole.UserRole).get('kind') == 'path'}
        from .appearance import symbol_icon
        for p in paths:
            if p in existing:
                continue
            item = QListWidgetItem(p.name)
            item.setIcon(symbol_icon('note', self.shell.colors.accent))
            item.setToolTip(str(p))
            item.setData(Qt.ItemDataRole.UserRole, {'kind': 'system', 'path': p})
            self.list.addItem(item)
        self.status.setText(f'{self.list.count()} resultados · {len(paths)} del sistema')
        self.locate = None

    # Indica plocate faltante para solo programas y notas
    def handle_locate_error(self, proc, error):
        if proc != self.locate:
            return
        if error == QProcess.ProcessError.FailedToStart:
            self.status.setText('Falta plocate: solo se muestran programas y notas.')
        self.locate = None
