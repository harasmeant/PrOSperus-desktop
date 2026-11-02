# SPDX-License-Identifier: GPL-3.0-only
"""Aplicación «Ramas»: personaliza las ramas del mapa de la carpeta actual (cwd).

Por defecto el estilo sale del fondo; aquí se puede fijar a mano y retocar curvatura,
grosor y opacidad, y elegir adornos (piezas de serie o imágenes propias) y cada cuánto salen.
Se guarda en la carpeta y lo heredan sus subcarpetas."""
import math
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QSlider, QSpinBox,
                               QVBoxLayout, QWidget)

from . import branch_style
from .appearance import Palette, paint_wallpaper, wallpaper_hue, wallpaper_traits
from .branches import BUILTIN_ORNAMENTS, branch
from .map_layout import radial_slots
from .window_header import WindowHeader

STYLE_LABELS = (('straight', 'Art déco'), ('magic', 'Art nouveau'), ('detail', 'Brotes'))
TWEAK_LABELS = (('curl', 'Curvatura'), ('width', 'Grosor'), ('opacity', 'Opacidad'))
PLACE_LABELS = (('rama', 'Sobre la rama'), ('brote', 'Al final de un tallo'))


def find_wallpaper(folder):
    """Fondo de la carpeta o de la más cercana hacia arriba (sin pasar de la carpeta personal)."""
    current = Path(folder)
    while True:
        for suffix in ('png', 'jpg', 'jpeg', 'webp', 'avif'):
            candidate = current / ('wallpaper.' + suffix)
            if candidate.is_file():
                return candidate
        if current == Path.home() or current.parent == current:
            return None
        current = current.parent


class Preview(QWidget):
    """Mapa en miniatura: carpeta central y seis tarjetas con las ramas tal como quedarían."""

    def __init__(self, wallpaper, palette):
        super().__init__()
        self.wallpaper, self.colors, self.traits = wallpaper, palette, {}
        self.setMinimumSize(520, 300)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect())
        clip = QPainterPath(); clip.addRoundedRect(rect, 12, 12); p.setClipPath(clip)
        paint_wallpaper(p, rect, self.wallpaper, self.colors.base, (60, 20, 60), self.colors.shade)
        w, h = rect.width(), rect.height()
        centre = QRectF(w / 2 - 70, h / 2 - 30, 140, 60)
        cards = [QRectF(x - 55, y - 18, 110, 36) for x, y in radial_slots(6, w / 2, h / 2, w * .34, h * .34)]
        visible = QPainterPath(); visible.addRect(rect)
        for card in [centre] + cards:
            hole = QPainterPath(); hole.addRoundedRect(card, 9, 9); visible = visible.subtracted(hole)
        p.setClipPath(visible)
        pearl = QColor(self.colors.text)
        pearl.setAlpha(max(0, min(255, round(165 * self.traits.get('opacity', 1)))))
        for k, card in enumerate(cards):
            branch(p, centre.center(), card.center(), 6.5, 2, pearl, k, 4, traits=self.traits)
        p.setClipping(False)
        p.setPen(QPen(QColor(self.colors.border), 1.2))
        for card, text in [(centre, Path.cwd().name)] + [(c, 'Carpeta %d' % (i + 1)) for i, c in enumerate(cards)]:
            p.setBrush(QColor(self.colors.panel)); p.drawRoundedRect(card, 9, 9)
            p.setPen(QColor(self.colors.text)); p.drawText(card, Qt.AlignmentFlag.AlignCenter, text)
            p.setPen(QPen(QColor(self.colors.border), 1.2))


class BranchSettings(QWidget):
    def __init__(self, folder=None):
        super().__init__()
        self.folder = Path(folder or Path.cwd())
        self.setWindowTitle('Ramas')
        self.resize(1000, 720)
        self.wallpaper = find_wallpaper(self.folder)
        self.auto_traits = {}
        hue = None
        if self.wallpaper:
            modified = self.wallpaper.stat().st_mtime_ns
            self.auto_traits = wallpaper_traits(self.wallpaper, modified) or {}
            hue = wallpaper_hue(self.wallpaper, modified)
        self.colors = Palette(hue if hue is not None else 145)
        self.setObjectName('branchSettings')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        c = self.colors
        self.setStyleSheet(c.css() + f'''
        QWidget#branchSettings {{ background: {c.base}; }}
        QSlider::groove:horizontal {{ height: 4px; background: {c.panel}; border-radius: 2px; }}
        QSlider::sub-page:horizontal {{ background: {c.accent}; border-radius: 2px; }}
        QSlider::handle:horizontal {{ width: 14px; margin: -6px 0; border-radius: 7px; background: {c.text}; }}
        QSlider::handle:horizontal:disabled, QSlider::sub-page:horizontal:disabled {{ background: {c.border}; }}
        ''')

        layout = QVBoxLayout(self); layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(WindowHeader('Ramas para: {}'.format(self.folder.name), self))
        self.preview = Preview(self.wallpaper, self.colors)
        layout.addWidget(self.preview, 1)

        saved = branch_style.raw(self.folder)
        self.auto = QCheckBox('Automático: el estilo sale del fondo')
        self.auto.setChecked(saved.get('auto', True))
        layout.addWidget(self.auto)
        columns = QHBoxLayout(); layout.addLayout(columns)
        form = QFormLayout(); columns.addLayout(form, 1)
        self.sliders = {}
        for key, label in STYLE_LABELS:
            value = saved.get(key, self.auto_traits.get(key, .4 if key == 'detail' else 0))
            self.sliders[key] = self.slider(form, label, 0, 100, value * 100)
        for key, label in TWEAK_LABELS:
            low, high = branch_style.TWEAKS[key]
            self.sliders[key] = self.slider(form, label, round(low * 100), round(high * 100), saved.get(key, 1) * 100)
        columns.addLayout(self.build_ornaments(saved), 1)
        self.measured = QLabel(); self.measured.setObjectName('muted')
        layout.addWidget(self.measured)

        buttons = QHBoxLayout(); buttons.addStretch(1)
        for text, callback in (('Volver a automático', self.reset), ('Guardar en esta carpeta', self.save), ('Cerrar', self.close)):
            button = QPushButton(text); button.clicked.connect(callback); buttons.addWidget(button)
        layout.addLayout(buttons)
        self.auto.toggled.connect(self.update_preview)
        self.update_preview()

    def build_ornaments(self, saved):
        """Lista de adornos: cada uno con su frecuencia, sitio, tamaño y tinte."""
        box = QVBoxLayout()
        box.addWidget(QLabel('Adornos'))
        self.ornaments = []
        source = branch_style.settings_file(self.folder)
        for item in branch_style.clean({'ornaments': saved.get('ornaments', [])}, source.parent if source else None).get('ornaments', []):
            self.ornaments.append(item)
        self.ornament_list = QListWidget(); self.ornament_list.setIconSize(self.ornament_list.iconSize())
        self.ornament_list.currentRowChanged.connect(self.select_ornament)
        box.addWidget(self.ornament_list, 1)
        row = QHBoxLayout()
        add = QPushButton('Añadir adorno')
        menu = QMenu(add)
        for kind, label in BUILTIN_ORNAMENTS.items():
            menu.addAction(label, lambda kind=kind: self.add_ornament({'kind': kind}))
        menu.addSeparator()
        menu.addAction('Imagen propia…', self.add_image)
        add.setMenu(menu)
        remove = QPushButton('Quitar'); remove.clicked.connect(self.remove_ornament)
        row.addWidget(add); row.addWidget(remove); row.addStretch(1)
        box.addLayout(row)
        edit = QFormLayout()
        self.every = QSpinBox(); self.every.setRange(1, 20); self.every.setPrefix('1 de cada '); self.every.setSuffix(' brotes')
        self.place = QComboBox()
        for key, label in PLACE_LABELS:
            self.place.addItem(label, key)
        self.size = QSlider(Qt.Orientation.Horizontal); self.size.setRange(30, 300)
        self.tint = QCheckBox('Teñir con el color de las ramas')
        edit.addRow('Cada cuánto', self.every); edit.addRow('Dónde', self.place)
        edit.addRow('Tamaño', self.size); edit.addRow('', self.tint)
        box.addLayout(edit)
        self.every.valueChanged.connect(self.edit_ornament); self.place.currentIndexChanged.connect(self.edit_ornament)
        self.size.valueChanged.connect(self.edit_ornament); self.tint.toggled.connect(self.edit_ornament)
        self.refresh_ornaments()
        return box

    def ornament_label(self, item):
        name = item['file'] if item['kind'] == 'imagen' else BUILTIN_ORNAMENTS[item['kind']]
        place = dict(PLACE_LABELS)[item['place']].lower()
        return f"{name} · 1 de cada {item['every']} · {place}"

    def refresh_ornaments(self, row=None):
        self.ornament_list.blockSignals(True)
        self.ornament_list.clear()
        for item in self.ornaments:
            entry = QListWidgetItem(self.ornament_label(item))
            if item['kind'] == 'imagen':
                from PySide6.QtGui import QIcon
                entry.setIcon(QIcon(str(item['path'])))
            self.ornament_list.addItem(entry)
        self.ornament_list.blockSignals(False)
        if self.ornaments:
            self.ornament_list.setCurrentRow(min(row if row is not None else 0, len(self.ornaments) - 1))
        self.select_ornament(self.ornament_list.currentRow())

    def select_ornament(self, row):
        editing = 0 <= row < len(self.ornaments)
        for widget in (self.every, self.place, self.size, self.tint):
            widget.setEnabled(editing); widget.blockSignals(True)
        if editing:
            item = self.ornaments[row]
            self.every.setValue(item['every']); self.place.setCurrentIndex(self.place.findData(item['place']))
            self.size.setValue(round(item['size'] * 100)); self.tint.setChecked(item['tint'])
        for widget in (self.every, self.place, self.size, self.tint):
            widget.blockSignals(False)

    def edit_ornament(self, *_):
        row = self.ornament_list.currentRow()
        if not 0 <= row < len(self.ornaments):
            return
        self.ornaments[row].update(every=self.every.value(), place=self.place.currentData(),
                                   size=self.size.value() / 100, tint=self.tint.isChecked())
        self.ornament_list.item(row).setText(self.ornament_label(self.ornaments[row]))
        self.update_preview()

    def add_ornament(self, item):
        if len(self.ornaments) >= branch_style.MAX_ORNAMENTS:
            QMessageBox.information(self, 'Adornos', 'Como mucho %d adornos.' % branch_style.MAX_ORNAMENTS); return
        item = {'every': 3, 'place': 'rama', 'size': 1.0, 'tint': True, **item}
        self.ornaments.append(item); self.refresh_ornaments(len(self.ornaments) - 1); self.update_preview()

    def add_image(self, path=None):
        path = path or QFileDialog.getOpenFileName(self, 'Imagen para adorno', str(Path.home()),
                                                   'Imágenes (*.png *.jpg *.jpeg *.webp *.gif)')[0]
        if not path:
            return
        try:
            name = branch_style.add_image(self.folder, path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'Error', str(error)); return
        # Las imágenes con transparencia quedan mejor teñidas; una foto, con sus colores.
        self.add_ornament({'kind': 'imagen', 'file': name, 'path': self.folder / branch_style.IMAGES / name,
                           'tint': Path(name).suffix.lower() in ('.png', '.webp', '.gif')})

    def remove_ornament(self):
        row = self.ornament_list.currentRow()
        if 0 <= row < len(self.ornaments):
            del self.ornaments[row]; self.refresh_ornaments(row); self.update_preview()

    def slider(self, form, label, low, high, value):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(low, high); slider.setValue(round(value))
        slider.valueChanged.connect(self.update_preview)
        form.addRow(label, slider)
        return slider

    def current(self, for_saving=False):
        data = {'auto': self.auto.isChecked()}
        for key in branch_style.STYLE_KEYS + tuple(branch_style.TWEAKS):
            data[key] = round(self.sliders[key].value() / 100, 2)
        data['ornaments'] = []
        for item in getattr(self, 'ornaments', []):
            entry = {key: item[key] for key in ('kind', 'every', 'place', 'size', 'tint')}
            if item['kind'] == 'imagen':
                # Una imagen heredada de una carpeta de arriba se copia aquí para que viaje con esta.
                entry['file'] = branch_style.add_image(self.folder, item['path']) if for_saving else item['file']
            data['ornaments'].append(entry)
        return data

    def preview_traits(self):
        data = self.current()
        overrides = branch_style.clean({k: v for k, v in data.items() if k != 'ornaments'})
        if self.ornaments:
            overrides['ornaments'] = [dict(item) for item in self.ornaments]
        return branch_style.merge(self.auto_traits, overrides)

    def update_preview(self):
        automatic = self.auto.isChecked()
        for key in branch_style.STYLE_KEYS:
            self.sliders[key].setEnabled(not automatic)
        self.preview.traits = self.preview_traits()
        if self.auto_traits:
            self.measured.setText('Según el fondo: art déco {:.0%} · art nouveau {:.0%} · brotes {:.0%}'.format(
                self.auto_traits['straight'], self.auto_traits['magic'], self.auto_traits['detail']))
        else:
            self.measured.setText('Esta carpeta no tiene fondo: en automático se usa la enredadera.')
        self.preview.update()

    def save(self):
        try:
            branch_style.save(self.folder, self.current(for_saving=True))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'Error', str(error)); return
        self.close()

    def reset(self):
        try:
            branch_style.reset(self.folder)
        except OSError as error:
            QMessageBox.warning(self, 'Error', str(error)); return
        self.auto.setChecked(True)
        for key, slider in self.sliders.items():
            slider.setValue(round((self.auto_traits.get(key, .4) if key == 'detail' else
                                   self.auto_traits.get(key, 0) if key in branch_style.STYLE_KEYS else 1) * 100))


def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName('org.prosperus.Branches')
    window = BranchSettings()
    window.show()
    if '--screenshot' in sys.argv:
        from PySide6.QtCore import QTimer
        target = sys.argv[sys.argv.index('--screenshot') + 1]
        QTimer.singleShot(400, lambda: (window.grab().save(target), app.quit()))
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
