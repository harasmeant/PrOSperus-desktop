# SPDX-License-Identifier: GPL-3.0-only
"""Selector de fondos de la carpeta actual (cwd): imagen, tono (contraste, suavidad, momentos del día)
y horario para que el fondo cambie a lo largo del día."""
import os
import sys
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QImage
from .window_header import WindowHeader
from .theme_state import current_palette
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QMessageBox,
    QListView, QComboBox, QSpinBox, QFormLayout
)
from . import wallpaper_schedule as schedule
from .recolour import recolour
from .tones import GROUPS, TONES, ORIGINAL, toned_wallpaper

SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.avif')


def apply_wallpaper(source, folder):
    """Copia un wallpaper desde ``source`` a ``folder`` respetando los backups anteriores.

    Si en ``folder`` existen archivos ``wallpaper.*`` (png, jpg, jpeg, webp, avif) se renombran
    a ``.wallpaper-anterior.<ext>``. Si ``folder`` es el home o '/' o no es un directorio, lanza
    ``ValueError`` con el mensaje español 'Elige una carpeta de proyecto.'.
    """
    folder = Path(folder)
    if folder == Path.home() or folder == Path('/') or not folder.is_dir():
        raise ValueError('Elige una carpeta de proyecto.')

    # Conservar wallpapers anteriores mediante renombrado (no se eliminan)
    for f in folder.glob('wallpaper.*'):
        if f.suffix.lower() in SUFFIXES and f.stem == 'wallpaper':
            backup = f.parent / ('.wallpaper-anterior' + f.suffix)
            os.replace(f, backup)

    target = folder / ('wallpaper' + Path(source).suffix.lower())
    shutil.copyfile(source, target)
    return target


def base_wallpaper(folder):
    for suffix in SUFFIXES:
        candidate = Path(folder) / ('wallpaper' + suffix)
        if candidate.is_file():
            return candidate
    return None


def add_hour(folder, hour, source, tone):
    """Pone a la hora `hour` la imagen `source` (None = el fondo de la carpeta) con el tono `tone`.
    La imagen se copia como wallpaper-HH.ext para que el proyecto se lleve su horario si se mueve.
    Devuelve la imagen que se verá a esa hora."""
    folder = Path(folder)
    if folder == Path.home() or folder == Path('/') or not folder.is_dir():
        raise ValueError('Elige una carpeta de proyecto.')
    data = remove_hour(folder, hour)
    image = None
    if source is not None:
        image = f'wallpaper-{hour:02d}{Path(source).suffix.lower()}'
        shutil.copyfile(source, folder / image)
    data['horas'] = sorted(data['horas'] + [{'hora': hour, 'imagen': image, 'tono': tone}], key=lambda e: e['hora'])
    schedule.save(folder, data)
    return folder / image if image else base_wallpaper(folder)


def remove_hour(folder, hour):
    """Quita la hora del horario y su imagen, si ninguna otra hora la usa."""
    folder = Path(folder)
    data = schedule.load(folder)
    for entry in [e for e in data['horas'] if e['hora'] == hour]:
        data['horas'].remove(entry)
        if entry['imagen'] and not any(e['imagen'] == entry['imagen'] for e in data['horas']):
            (folder / entry['imagen']).unlink(missing_ok=True)
    schedule.save(folder, data)
    return data


def tone_label(name):
    return 'Original del fondo' if name == ORIGINAL else TONES[name].label if name in TONES else name


def thumbnail(path, size=QSize(220, 138)):
    pixmap = QPixmap(str(path)) if path else QPixmap()
    if pixmap.isNull():
        return QPixmap()
    return pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)


def plain_icon(pixmap):
    """Icono que no se tiñe al seleccionarlo (Qt lo azulea por defecto)."""
    icon = QIcon(pixmap)
    icon.addPixmap(pixmap, QIcon.Mode.Selected)
    return icon


# Imagen, tono y horario del fondo de la carpeta actual.
class WallpaperPicker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Fondo de pantalla')
        self.resize(1060, 680)
        self.folder = Path.cwd()
        # Mismo tono que el proyecto que se ve en el escritorio.
        self.setStyleSheet(current_palette().css() + 'WallpaperPicker {{ background: {}; }}'.format(current_palette().base))
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(WindowHeader('Fondo para: {}'.format(self.folder.name), self))
        body = QHBoxLayout(); body.setSpacing(18); layout.addLayout(body, 1)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(200, 125))
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_widget.setSpacing(6)
        body.addWidget(self.list_widget, 3)
        # La primera es el fondo que ya tiene la carpeta: sirve para cambiarle solo el tono o ponerlo a una hora.
        current = base_wallpaper(self.folder)
        if current:
            item = QListWidgetItem(plain_icon(thumbnail(current, QSize(200, 125))), 'Fondo actual')
            item.setData(Qt.ItemDataRole.UserRole, None); self.list_widget.addItem(item)
        # Directorio de wallpapers por defecto, sobreescribible por PROSPERUS_WALLPAPERS
        images_dir = Path(os.environ.get('PROSPERUS_WALLPAPERS', '/usr/share/prosperus/wallpapers'))
        if images_dir.is_dir():
            for filename in sorted(f for f in os.listdir(images_dir) if f.lower().endswith(SUFFIXES)):
                picture = thumbnail(images_dir / filename, QSize(200, 125))
                if picture.isNull():
                    continue
                item = QListWidgetItem(plain_icon(picture), '')
                item.setData(Qt.ItemDataRole.UserRole, images_dir / filename); self.list_widget.addItem(item)
        if not self.list_widget.count():
            body.insertWidget(0, QLabel('No hay fondos instalados.'))

        side = QVBoxLayout(); side.setSpacing(10); body.addLayout(side, 2)
        self.preview = QLabel(); self.preview.setFixedSize(360, 225); self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setObjectName('muted'); side.addWidget(self.preview)
        form = QFormLayout(); form.setSpacing(10)
        self.tone = QComboBox()
        self.tone.addItem(tone_label(ORIGINAL), ORIGINAL)
        for group in GROUPS:
            self.tone.insertSeparator(self.tone.count())
            self.tone.addItem(group.upper(), None)
            self.tone.model().item(self.tone.count() - 1).setEnabled(False)
            for name, tone in TONES.items():
                if tone.group == group:
                    self.tone.addItem('   ' + tone.label, name)
        self.tone.setMaxVisibleItems(18)
        form.addRow('Tono', self.tone)
        side.addLayout(form)
        use = QPushButton('Usar como fondo de la carpeta'); use.clicked.connect(lambda: self._on_apply()); side.addWidget(use)

        heading = QLabel('POR HORAS'); heading.setObjectName('section'); side.addWidget(heading)
        hint = QLabel('Elige imagen y tono, la hora, y añádelo: el fondo cambia solo a esa hora, fundiéndose poco a poco.')
        hint.setObjectName('muted'); hint.setWordWrap(True); side.addWidget(hint)
        self.hours = QListWidget(); self.hours.setIconSize(QSize(64, 40)); self.hours.setMinimumHeight(140)
        side.addWidget(self.hours, 1)
        row = QHBoxLayout()
        self.hour = QSpinBox(); self.hour.setRange(0, 23); self.hour.setSuffix(':00'); self.hour.setWrapping(True)
        import time
        self.hour.setValue(time.localtime().tm_hour)
        add = QPushButton('Añadir a esta hora'); add.clicked.connect(self.add_hour)
        remove = QPushButton('Quitar'); remove.clicked.connect(self.remove_hour)
        row.addWidget(self.hour); row.addWidget(add, 1); row.addWidget(remove); side.addLayout(row)
        fade_row = QFormLayout()
        self.fade = QSpinBox(); self.fade.setRange(0, schedule.MAX_FADE); self.fade.setSuffix(' min')
        self.fade.setValue(schedule.load(self.folder)['fundido'])
        self.fade.valueChanged.connect(self.save_fade)
        fade_row.addRow('Fundido entre horas', self.fade); side.addLayout(fade_row)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_close = QPushButton('Cerrar')
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        # Doble clic en cualquier elemento también aplica el wallpaper
        self.list_widget.itemDoubleClicked.connect(lambda item=None: self._on_apply(item))
        self.list_widget.currentItemChanged.connect(lambda *_: self.update_preview())
        self.tone.currentIndexChanged.connect(lambda *_: self.update_preview())
        self.hours.currentItemChanged.connect(self.pick_entry)
        btn_close.clicked.connect(self.close)

        saved = schedule.load(self.folder)['tono']
        self.tone.setCurrentIndex(max(0, self.tone.findData(saved)))
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        self.refresh_hours()

    def selected_source(self):
        """(ruta para la vista previa, ruta a copiar o None si es el fondo actual)."""
        item = self.list_widget.currentItem()
        if item is None:
            return None, None
        source = item.data(Qt.ItemDataRole.UserRole)
        return (base_wallpaper(self.folder) if source is None else Path(source)), source

    def update_preview(self):
        path, _ = self.selected_source()
        name = self.tone.currentData() or ORIGINAL
        image = QImage(str(path)) if path else QImage()
        if image.isNull():
            self.preview.setText('Sin imagen'); return
        image = image.scaled(360, 225, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        if name in TONES:
            image = recolour(image, *TONES[name].recipe)[0]
        self.preview.setPixmap(QPixmap.fromImage(image).copy(0, 0, 360, 225))

    def refresh_hours(self):
        self.hours.clear()
        base = base_wallpaper(self.folder)
        for entry in schedule.load(self.folder)['horas']:
            path = self.folder / entry['imagen'] if entry['imagen'] else base
            item = QListWidgetItem(plain_icon(thumbnail(path, QSize(64, 40))),
                                   f"{entry['hora']:02d}:00  ·  {tone_label(entry['tono'])}")
            item.setData(Qt.ItemDataRole.UserRole, entry['hora']); self.hours.addItem(item)
        if not self.hours.count():
            placeholder = QListWidgetItem('Sin horario: se ve siempre el mismo fondo.')
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags); self.hours.addItem(placeholder)

    def pick_entry(self, item, _previous=None):
        hour = item.data(Qt.ItemDataRole.UserRole) if item else None
        if hour is not None:
            self.hour.setValue(hour)

    def add_hour(self):
        path, source = self.selected_source()
        if path is None:
            QMessageBox.warning(self, 'Aviso', 'Elige un fondo.'); return
        name = self.tone.currentData() or ORIGINAL
        try:
            image = add_hour(self.folder, self.hour.value(), source, name)
            # Recolorear lleva unos segundos: mejor ahora que cuando el escritorio cambie de hora.
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                toned_wallpaper(image, name)
            finally:
                QApplication.restoreOverrideCursor()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'Error', str(error)); return
        self.refresh_hours()

    def remove_hour(self):
        item = self.hours.currentItem()
        hour = item.data(Qt.ItemDataRole.UserRole) if item else None
        if hour is None:
            return
        try:
            remove_hour(self.folder, hour)
        except OSError as error:
            QMessageBox.warning(self, 'Error', str(error)); return
        self.refresh_hours()

    def save_fade(self, minutes):
        data = schedule.load(self.folder); data['fundido'] = minutes
        try:
            schedule.save(self.folder, data)
        except OSError as error:
            QMessageBox.warning(self, 'Error', str(error))

    def _on_apply(self, item=None):
        if item is not None:
            self.list_widget.setCurrentItem(item)
        path, source = self.selected_source()
        if path is None:
            QMessageBox.warning(self, 'Aviso', 'Elige un fondo.')
            return
        name = self.tone.currentData() or ORIGINAL
        try:
            target = path if source is None else apply_wallpaper(source, self.folder)
            data = schedule.load(self.folder); data['tono'] = name; schedule.save(self.folder, data)
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                toned_wallpaper(target, name)
            finally:
                QApplication.restoreOverrideCursor()
            self.close()
        except (OSError, ValueError) as e:
            # Mostrar mensaje descriptivo del error
            QMessageBox.warning(self, 'Error', str(e))


# Punto de entrada del selector de fondos
def main():
    app = QApplication(sys.argv)
    # Establecer nombre de aplicación para el gestor de ventanas del escritorio
    app.setDesktopFileName('org.prosperus.Wallpapers')
    from .appearance import speak_spanish; speak_spanish(app)
    window = WallpaperPicker()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
