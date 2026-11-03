# SPDX-License-Identifier: GPL-3.0-only
"""Vigila la carpeta de entrada (descargas) y reparte cada archivo en el proyecto que se ve.

Una descarga se mueve cuando ha terminado (sin .part/.crdownload) y su tamaño no cambia entre dos
miradas. Con una extensión desconocida se pregunta el destino una sola vez (file_routing)."""
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton, QVBoxLayout)

from . import file_routing as routing


class DestinationDialog(QDialog):
    """¿Dónde van los archivos .ext? Elegir una carpeta de tipo o escribir una nueva."""
    def __init__(self, parent, name, project):
        super().__init__(parent)
        ext = routing.extension(name) or name
        self.setWindowTitle('¿Dónde guardo los .' + ext + '?')
        layout = QVBoxLayout(self)
        text = QLabel(f'«{name}» ha llegado a {Path(project).name}. ¿En qué carpeta van los archivos .{ext}?\n'
                      'Se recordará para todos los proyectos (puedes cambiarlo en Controles › Destinos de archivos).')
        text.setWordWrap(True); layout.addWidget(text)
        self.choice = QComboBox(); self.choice.addItems(routing.type_folders(project)); layout.addWidget(self.choice)
        self.new = QLineEdit(); self.new.setPlaceholderText('…o una carpeta nueva: Modelos 3D, Partituras…')
        layout.addWidget(self.new)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Guardar aquí')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Más tarde')
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def folder(self):
        written = self.new.text().strip()
        return written if routing.safe_folder(written) else self.choice.currentText()


class DestinationsDialog(QDialog):
    """Destinos recordados por extensión, para olvidarlos (se volverá a preguntar)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Destinos de archivos'); self.resize(460, 360)
        layout = QVBoxLayout(self)
        info = QLabel('Las descargas van al proyecto que tienes abierto, en la carpeta de su tipo. '
                      'Estas extensiones tienen un destino elegido por ti:')
        info.setWordWrap(True); layout.addWidget(info)
        self.list = QListWidget(); layout.addWidget(self.list)
        row = QHBoxLayout()
        forget = QPushButton('Olvidar'); forget.clicked.connect(self.forget); row.addWidget(forget)
        row.addStretch(1)
        close = QPushButton('Cerrar'); close.clicked.connect(self.accept); row.addWidget(close)
        layout.addLayout(row)
        self.fill()

    def fill(self):
        self.list.clear()
        for ext, folder in sorted(routing.load_memory().items()):
            item = QListWidgetItem(f'.{ext}  →  {folder}'); item.setData(256, ext); self.list.addItem(item)
        if not self.list.count():
            self.list.addItem('Ninguna todavía: se pregunta la primera vez que llega una extensión desconocida.')

    def forget(self):
        item = self.list.currentItem()
        ext = item.data(256) if item else None
        if ext:
            memory = routing.load_memory(); memory.pop(ext, None); routing.save_memory(memory); self.fill()


class Incoming(QObject):
    message = Signal(str)
    arrived = Signal(Path)

    def __init__(self, parent, project_getter, directory=None):
        super().__init__(parent)
        self.parent_widget, self.project_getter = parent, project_getter
        self.directory = Path(directory or routing.incoming_dir())
        self.directory.mkdir(parents=True, exist_ok=True)
        self.sizes, self.asking = {}, False
        self.watcher = QFileSystemWatcher([str(self.directory)], self)
        self.timer = QTimer(self, singleShot=True, interval=1500, timeout=self.scan)
        self.watcher.directoryChanged.connect(lambda _: self.timer.start())
        self.timer.start()

    def scan(self):
        if self.asking:
            return
        pending = False
        for path in sorted(self.directory.iterdir()):
            if not path.is_file() or routing.is_partial(path.name):
                pending = pending or path.is_file()
                continue
            size = path.stat().st_size
            if self.sizes.get(path.name) != size:
                # Aún puede estar escribiéndose: se mira otra vez dentro de un momento.
                self.sizes[path.name] = size; pending = True
                continue
            self.sizes.pop(path.name, None)
            if not self.deliver(path):
                break
        if pending:
            self.timer.start()

    def deliver(self, path):
        """Mueve un archivo; False si hay que dejarlo para más tarde."""
        project = self.project_getter()
        if project is None:
            self.message.emit('Abre un proyecto para recibir «' + path.name + '»: está en la carpeta de entrada.')
            return False
        try:
            target = routing.route(path, project, routing.load_memory())
            if target is None:
                self.asking = True
                dialog = DestinationDialog(self.parent_widget, path.name, project)
                accepted = dialog.exec()
                self.asking = False
                if not accepted:
                    return False
                folder = dialog.folder()
                ext = routing.extension(path.name)
                if ext:
                    memory = routing.load_memory(); memory[ext] = folder; routing.save_memory(memory)
                target = routing.move_to(path, Path(project) / folder)
        except OSError as error:
            self.message.emit('No se pudo guardar «' + path.name + '»: ' + str(error))
            return False
        self.message.emit(f'Guardado en {Path(project).name} › {target.parent.name}: {target.name}')
        self.arrived.emit(target)
        return True
