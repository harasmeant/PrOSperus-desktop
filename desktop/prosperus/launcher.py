"""Asynchronous GIO launcher, with explicitly pinned global favourites."""
# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
import sys

from PySide6.QtCore import QObject, QProcess, QSettings, Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from .model import searchable


class ApplicationService(QObject):
    completed = Signal(str, object)
    failed = Signal(str)
    favorites_changed = Signal()

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
        self.process = QProcess(self)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)

    def run(self, action, desktop_id=None):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.failed.emit('Hay una operación de aplicaciones en curso.'); return
        self.action = action
        arguments = [str(Path(__file__).with_name('applications.py')), action]
        if desktop_id is not None:
            arguments.append(desktop_id)
        self.process.start(sys.executable, arguments)

    def process_error(self, error):
        self.failed.emit('No se pudo ejecutar el servicio de aplicaciones: ' + self.process.errorString())

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
    def __init__(self, shell):
        super().__init__(shell)
        # Imported here to keep the shell/launcher dependency one-way at load time.
        from .shell import button
        self.service = shell.apps
        self.setWindowTitle('Aplicaciones'); self.resize(650, 530)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Busca una aplicación de Fedora y fíjala en la barra.'))
        self.search = QLineEdit(); self.search.setPlaceholderText('Nombre, descripción o palabra clave…')
        self.search.textChanged.connect(self.render); layout.addWidget(self.search)
        self.list = QListWidget(); self.list.setStyleSheet('QListWidget { background: transparent; border: none; }')
        self.list.itemActivated.connect(lambda _: self.launch()); self.list.currentItemChanged.connect(self.selection_changed)
        layout.addWidget(self.list)
        self.status = QLabel(''); self.status.setWordWrap(True); layout.addWidget(self.status)
        row = QHBoxLayout()
        row.addWidget(button('Actualizar lista', self.refresh)); row.addStretch()
        self.favorite = button('Fijar', self.toggle_favorite); row.addWidget(self.favorite)
        self.open = button('Abrir', self.launch); row.addWidget(self.open); layout.addLayout(row)
        self.service.completed.connect(self.completed)
        self.service.failed.connect(self.report_error)
        self.service.favorites_changed.connect(self.render)
        self.finished.connect(self.disconnect_service)
        self.render()
        if not self.service.catalogue:
            self.refresh()

    def disconnect_service(self):
        self.service.completed.disconnect(self.completed)
        self.service.failed.disconnect(self.report_error)
        self.service.favorites_changed.disconnect(self.render)

    def report_error(self, message):
        if 'gi' in message and 'module' in message:
            message = 'Falta el componente de aplicaciones. Instala python3-gobject dentro de Fedora y pulsa Actualizar lista.'
        self.status.setText(message)

    def refresh(self):
        self.status.setText('Buscando aplicaciones instaladas…'); self.service.run('list')

    def completed(self, action, data):
        if action == 'list':
            self.render()
        elif action == 'launch':
            self.accept()

    def render(self):
        selected = self.selected()
        selected_id = selected['id'] if selected else None
        self.list.clear()
        favorites = {a['id'] for a in self.service.favorites}
        terms = searchable(self.search.text()).split()
        apps = [app for app in self.service.catalogue if all(t in searchable(' '.join([app['name'], app.get('description', ''), *app.get('keywords', [])])) for t in terms)]
        for app in sorted(apps, key=lambda a: (a['id'] not in favorites, searchable(a['name']))):
            item = QListWidgetItem(('★  ' if app['id'] in favorites else '') + app['name'])
            item.setToolTip(app.get('description', '')); item.setData(Qt.ItemDataRole.UserRole, app)
            self.list.addItem(item)
            if app['id'] == selected_id:
                self.list.setCurrentItem(item)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self.status.setText(f'{len(apps)} aplicaciones · Favoritas globales')
        self.selection_changed()

    def selected(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def selection_changed(self, *args):
        app = self.selected()
        self.open.setEnabled(app is not None); self.favorite.setEnabled(app is not None)
        self.favorite.setText('Desfijar' if app and any(a['id'] == app['id'] for a in self.service.favorites) else 'Fijar')

    def toggle_favorite(self):
        app = self.selected()
        if app:
            self.service.toggle_favorite(app)

    def launch(self):
        app = self.selected()
        if app:
            self.status.setText('Abriendo ' + app['name'] + '…'); self.service.run('launch', app['id'])
