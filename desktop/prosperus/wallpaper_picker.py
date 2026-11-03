# SPDX-License-Identifier: GPL-3.0-only
"""Selector de fondos de pantalla. Establece el wallpaper solo de la carpeta actual (cwd)."""
import os
import sys
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon
from .window_header import WindowHeader
from .theme_state import current_palette
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QMessageBox,
    QListView
)


def apply_wallpaper(source, folder):
    """Copia un wallpaper desde ``source`` a ``folder`` respetando los backups anteriores.

    Si en ``folder`` existen archivos ``wallpaper.*`` (png, jpg, jpeg, webp, avif) se renombran
    a ``.wallpaper-anterior.<ext>``. Si ``folder`` es el home o '/' o no es un directorio, lanza
    ``ValueError`` con el mensaje español 'Elige una carpeta de proyecto.'.
    """
    folder = Path(folder)
    if folder == Path.home() or folder == Path('/') or not folder.is_dir():
        raise ValueError('Elige una carpeta de proyecto.')

    suffixes = ('.png', '.jpg', '.jpeg', '.webp', '.avif')
    # Conservar wallpapers anteriores mediante renombrado (no se eliminan)
    for f in folder.glob('wallpaper.*'):
        if f.suffix.lower() in suffixes and f.stem == 'wallpaper':
            backup = f.parent / ('.wallpaper-anterior' + f.suffix)
            os.replace(f, backup)

    target = folder / ('wallpaper' + Path(source).suffix.lower())
    shutil.copyfile(source, target)
    return target


# Gestor y selector de fondos de pantalla para el proyecto actual.
class WallpaperPicker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Fondo de pantalla')
        self.resize(760, 520)
        # Mismo tono que el proyecto que se ve en el escritorio.
        self.setStyleSheet(current_palette().css() + 'WallpaperPicker {{ background: {}; }}'.format(current_palette().base))
        self._build_ui()

    def _build_ui(self):
        folder_name = Path.cwd().name
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(WindowHeader('Fondo para: {}'.format(folder_name), self))

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(220, 138))
        self.list_widget.setUniformItemSizes(True)

        # Directorio de wallpapers por defecto, sobreescribible por PROSPERUS_WALLPAPERS
        images_dir = Path(os.environ.get('PROSPERUS_WALLPAPERS', '/usr/share/prosperus/wallpapers'))

        if not images_dir.is_dir():
            lbl = QLabel('No hay fondos instalados.')
            layout.addWidget(lbl)
        else:
            files = sorted(f for f in os.listdir(images_dir)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
            if not files:
                lbl = QLabel('No hay fondos instalados.')
                layout.addWidget(lbl)
            else:
                for filename in files:
                    filepath = images_dir / filename
                    pixmap = QPixmap(str(filepath))
                    if pixmap.isNull():
                        continue
                    thumbnail = pixmap.scaled(220, 138,
                                              Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                              Qt.TransformationMode.SmoothTransformation)
                    icon = QIcon(thumbnail)
                    item = QListWidgetItem()
                    item.setIcon(icon)
                    item.setData(Qt.ItemDataRole.UserRole, filepath)
                    self.list_widget.addItem(item)
                layout.addWidget(self.list_widget)

        # Botones alineados a la derecha con un estiramiento
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_apply = QPushButton('Usar en esta carpeta')
        btn_close = QPushButton('Cerrar')
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        btn_apply.clicked.connect(lambda: self._on_apply())
        # Doble clic en cualquier elemento también aplica el wallpaper
        self.list_widget.itemDoubleClicked.connect(lambda item=None: self._on_apply(item))
        btn_close.clicked.connect(self.close)

    def _on_apply(self, item=None):
        if item is None:
            item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.warning(self, 'Aviso', 'Elige un fondo.')
            return
        src = Path(item.data(Qt.ItemDataRole.UserRole))
        try:
            # Aplicar wallpaper y cerrar ventana
            apply_wallpaper(src, Path.cwd())
            self.close()
        except (OSError, ValueError) as e:
            # Mostrar mensaje descriptivo del error
            QMessageBox.warning(self, 'Error', str(e))


def main():
    app = QApplication(sys.argv)
    # Establecer nombre de aplicación para el gestor de ventanas del escritorio
    app.setDesktopFileName('org.prosperus.Wallpapers')
    window = WallpaperPicker()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
