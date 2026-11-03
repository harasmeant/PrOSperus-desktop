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


class SortDialog(QDialog):
    """«Ordenar archivos sueltos»: lista con casillas y el destino de cada uno. No mueve nada hasta
    Aceptar. Notas (.md) y carpetas salen desmarcadas: se dejan sueltas a propósito en el mapa."""
    def __init__(self, parent, folder):
        super().__init__(parent)
        self.folder = Path(folder)
        self.setWindowTitle('Ordenar archivos sueltos'); self.resize(620, 480)
        layout = QVBoxLayout(self)
        info = QLabel(f'Archivos sueltos de {self.folder.name}. Marca los que quieras guardar en su carpeta; '
                      'puedes cambiar el destino o escribir uno nuevo.')
        info.setWordWrap(True); layout.addWidget(info)
        self.rows = []
        grid = QVBoxLayout()
        folders = routing.type_folders(self.folder)
        from PySide6.QtWidgets import QCheckBox, QScrollArea, QWidget
        for path, destination, checked in routing.sort_plan(self.folder, routing.load_memory()):
            row = QHBoxLayout()
            box = QCheckBox(('📁 ' if path.is_dir() else '') + path.name); box.setChecked(checked)
            target = QComboBox(); target.setEditable(True); target.addItems(folders)
            target.setCurrentText(destination or '')
            target.lineEdit().setPlaceholderText('¿Dónde?')
            row.addWidget(box, 1); row.addWidget(QLabel('→')); row.addWidget(target)
            grid.addLayout(row); self.rows.append((path, box, target))
        if not self.rows:
            grid.addWidget(QLabel('No hay archivos sueltos en esta carpeta.'))
        grid.addStretch(1)
        holder = QWidget(); holder.setLayout(grid)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(holder); layout.addWidget(scroll, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Mover los marcados')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def choices(self):
        """[(ruta, carpeta destino)] de las filas marcadas con un destino válido."""
        return [(path, target.currentText().strip()) for path, box, target in self.rows
                if box.isChecked() and routing.safe_folder(target.currentText()) and target.currentText().strip() != path.name]


def move_files(parent, choices, remember=True):
    """Mueve [(ruta, carpeta)] a la carpeta de tipo junto a cada archivo; recuerda las extensiones
    nuevas. Devuelve (movidos, errores)."""
    memory, moved, errors = routing.load_memory(), [], []
    for path, folder in choices:
        is_file = path.is_file()
        try:
            moved.append(routing.move_to(path, path.parent / folder))
        except OSError as error:
            errors.append(f'{path.name}: {error}'); continue
        ext = routing.extension(path.name)
        if remember and is_file and ext and routing.folder_for(path.name, memory) is None:
            memory[ext] = folder
    if remember:
        routing.save_memory(memory)
    return moved, errors


def ask_folder(parent, path):
    """Carpeta para un archivo concreto: la regla, o el diálogo si la extensión es desconocida
    (y entonces se recuerda). None si se cancela."""
    memory = routing.load_memory()
    folder = routing.folder_for(path.name, memory)
    if folder is not None:
        return folder
    dialog = DestinationDialog(parent, path.name, path.parent)
    if not dialog.exec():
        return None
    folder = dialog.folder()
    ext = routing.extension(path.name)
    if ext:
        memory[ext] = folder; routing.save_memory(memory)
    return folder
