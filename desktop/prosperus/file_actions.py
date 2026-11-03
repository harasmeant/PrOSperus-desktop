"""File clipboard and background copying shared by the map and explorer."""
# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path

from PySide6.QtCore import QMimeData, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu

from .transfers import copy_into


# Convierte QMimeData en rutas locales, validando que sean archivos del sistema
def local_paths(mime):
    if mime is None or not mime.hasUrls():
        return []
    urls = mime.urls()
    if any(not url.isLocalFile() for url in urls):
        raise ValueError('Selecciona archivos locales; no se importan enlaces de Internet.')
    return [Path(url.toLocalFile()) for url in urls]


# Worker que ejecuta copias en un hilo separado para no bloquear la interfaz
class CopyWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, vault, sources, destination):
        super().__init__()
        self.vault, self.sources, self.destination = vault, sources, destination

    @Slot()
    def run(self):
        try:
            self.completed.emit(copy_into(self.vault, self.sources, self.destination))
        except (OSError, ValueError) as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


# Gestor de acciones de archivos (copiar, pegar, importar) con soporte de hilo de fondo
class FileActions(QObject):
    changed = Signal()
    message = Signal(str)
    def __init__(self, shell):
        super().__init__(shell)
        self.shell = shell
        self.thread = None
        self.worker = None

    @property
    def busy(self):
        return self.thread is not None

    def report(self, text):
        self.shell.status.setText(text)
        self.message.emit(text)

    # Copia rutas al portapapeles con formato GNOME para mejor compatibilidad
    def copy(self, paths):
        if not paths:
            self.report('Selecciona una carpeta o una nota para copiar.'); return
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(str(path)) for path in paths]
        mime.setUrls(urls)
        mime.setData('x-special/gnome-copied-files', ('copy\n' + '\n'.join(url.toString() for url in urls)).encode())
        QApplication.clipboard().setMimeData(mime)
        self.report(f'{len(paths)} elementos copiados. Abre el destino y pulsa Ctrl+V.')

    # Pegar desde el portapapeles, iniciando transferencia si hay archivos válidos
    def paste(self, folder):
        try:
            paths = local_paths(QApplication.clipboard().mimeData())
            if not paths:
                raise ValueError('El portapapeles no contiene archivos o carpetas.')
            self.transfer(paths, folder)
        except (OSError, ValueError) as error:
            self.report(str(error))

    # Inicia una copia en segundo plano usando QThread para no bloquear la UI
    def transfer(self, paths, folder):
        if self.busy:
            self.report('Espera a que termine la copia actual.'); return
        self.report(f'Copiando {len(paths)} elementos a {folder.name}…')
        # El trabajador solo copia archivos. Las señales devuelven los cambios
        # al hilo principal: los widgets no se modifican desde el trabajador.
        self.thread = QThread(self)
        self.worker = CopyWorker(self.shell.vault, list(paths), folder)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.completed.connect(self.completed)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.finished)
        self.thread.start()

    @Slot(str)
    def failed(self, error):
        self.report('No se ha completado la copia: ' + error)

    @Slot(object)
    def completed(self, paths):
        self.shell.refresh_projects()
        self.report('Copiado: ' + ', '.join(path.name for path in paths))
        self.changed.emit()

    @Slot()
    def finished(self):
        thread = self.thread
        self.thread = None; self.worker = None
        thread.deleteLater()

    # Importa una carpeta completa mediante diálogo de archivo
    def import_folder(self, destination):
        source = QFileDialog.getExistingDirectory(self.shell, 'Elegir carpeta para copiar')
        if source:
            self.transfer([Path(source)], destination)

    # Importa archivos Markdown individuales
    def import_files(self, destination):
        paths, _ = QFileDialog.getOpenFileNames(self.shell, 'Elegir notas para copiar', '', 'Notas Markdown (*.md *.MD)')
        if paths:
            self.transfer([Path(p) for p in paths], destination)

    # Construye menú contextual con opciones de copiar/pegar/mover/imports
    def menu(self, parent, paths, destination, open_path=None, create_note=None, create_folder=None, create_project=None):
        menu = QMenu(parent)
        if len(paths) == 1:
            menu.addAction('Abrir', lambda: (open_path or self.shell.activate)(paths[0]))
        copy = menu.addAction('Copiar\tCtrl+C', lambda: self.copy(paths)); copy.setEnabled(bool(paths))
        duplicate = menu.addAction('Duplicar\tCtrl+D', lambda: self.transfer(paths, destination))
        duplicate.setEnabled(bool(paths) and not self.busy)
        paste = menu.addAction('Pegar aquí\tCtrl+V', lambda: self.paste(destination))
        mime = QApplication.clipboard().mimeData()
        paste.setEnabled(mime is not None and mime.hasUrls() and not self.busy)
        move = menu.addAction('Mover a otro proyecto…', lambda: self.shell.move_to(paths))
        move.setEnabled(bool(paths) and not self.busy)
        rename = menu.addAction('Renombrar…\tF2', lambda: self.shell.rename_path(paths[0]))
        rename.setEnabled(len(paths) == 1 and not self.busy)
        trash = menu.addAction('Mover a la papelera\tSupr', lambda: self.shell.trash_paths(paths))
        trash.setEnabled(bool(paths) and not self.busy)
        # Clasificar a mano (nunca automático): «Mover a Imágenes», o «a su carpeta» si son de varios tipos.
        files = [p for p in paths if p.is_file()]
        if files and len(files) == len(paths):
            from . import file_routing
            memory = file_routing.load_memory()
            kinds = {file_routing.folder_for(p.name, memory) for p in files}
            title = ('Mover a ' + kinds.pop()) if len(kinds) == 1 and None not in kinds else 'Mover a su carpeta…'
            sort = menu.addAction(title, lambda: self.shell.sort_into_folders(files))
            sort.setEnabled(not self.busy)
        if len(paths) == 1 and paths[0].is_dir():
            menu.addAction('Pegar dentro de esta carpeta', lambda: self.paste(paths[0]))
        menu.addSeparator()
        menu.addAction('Nueva nota', create_note or (lambda: self.shell.new_note(folder=destination)))
        menu.addAction('Nueva carpeta', create_folder or (lambda: self.shell.new_folder(folder=destination)))
        menu.addAction('Nuevo proyecto', create_project or self.shell.new_project)
        if not paths:
            menu.addAction('Ordenar archivos sueltos…', lambda: self.shell.sort_loose(destination))
        menu.addSeparator()
        menu.addAction('Importar carpeta…', lambda: self.import_folder(destination))
        menu.addAction('Importar notas…', lambda: self.import_files(destination))
        return menu
