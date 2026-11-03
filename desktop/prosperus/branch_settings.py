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
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox,
                               QVBoxLayout, QWidget)

from . import branch_style
from .appearance import Palette, paint_wallpaper, wallpaper_hue, wallpaper_traits
from .branches import BUILTIN_ORNAMENTS, branch
from .map_layout import map_metrics, radial_slots
from .window_header import WindowHeader

STYLE_LABELS = (('straight', 'Art déco'), ('magic', 'Art nouveau'), ('detail', 'Brotes'))
TWEAK_LABELS = (('curl', 'Curvatura'), ('width', 'Grosor'), ('opacity', 'Opacidad'))
PLACE_LABELS = (('rama', 'Sobre la rama'), ('brote', 'Al final de un tallo'))
SIDE_LABELS = (('horario', 'Horario'), ('antihorario', 'Antihorario'), ('ambos', 'Ambos lados, alternando'))
ORDER_LABELS = (('fuera', 'Del centro hacia fuera (la de fuera encima)'), ('dentro', 'De fuera hacia el centro (la de dentro encima)'))
# Barras del adorno: clave, etiqueta, mínimo, máximo, escala (valor guardado = barra / escala), unidad.
ORNAMENT_BARS = (('density', 'Frecuencia', 0, 100, 100, ''), ('angle', 'Ángulo', 0, 180, 1, '°'),
                 ('size', 'Tamaño', 30, 300, 100, '%'), ('opacity', 'Opacidad', 0, 100, 100, '%'))


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


# Formatos de pantalla para la vista previa (además de la pantalla real).
ASPECTS = (('16:9', 16 / 9), ('16:10', 16 / 10), ('21:9', 64 / 27), ('32:9', 32 / 9), ('4:3', 4 / 3))


def screen_ratio():
    screen = QApplication.primaryScreen()
    size = screen.size() if screen else None
    return (size.width() / size.height()) if size and size.height() else 16 / 9


def section(text):
    """Título de sección (estilo QLabel#section de la paleta)."""
    title = QLabel(text.upper()); title.setObjectName('section')
    return title


def airy(form):
    """Formularios con aire: filas separadas y etiquetas alineadas."""
    form.setVerticalSpacing(12); form.setHorizontalSpacing(18)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


class Preview(QWidget):
    """El escritorio entero a escala, con la proporción de la pantalla elegida y las mismas medidas
    que el mapa real (map_metrics): lo que se ve aquí es lo que saldrá."""

    def __init__(self, wallpaper, palette):
        super().__init__()
        self.wallpaper, self.colors, self.traits = wallpaper, palette, {}
        self.ratio = screen_ratio()
        # Tantas tarjetas como subcarpetas tenga (de 3 a 8, lo que cabe en una página del mapa).
        try:
            folders = sum(1 for entry in Path.cwd().iterdir() if entry.is_dir() and not entry.name.startswith('.'))
        except OSError:
            folders = 0
        self.count = max(3, min(8, folders))
        self.setMinimumSize(480, 220)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        # Pantalla virtual de 1080 px de alto con la proporción elegida, encajada en el recuadro.
        H = 1080.0; W = H * self.ratio
        k = min(self.width() / W, self.height() / H)
        p.translate((self.width() - W * k) / 2, (self.height() - H * k) / 2); p.scale(k, k)
        screen = QRectF(0, 0, W, H)
        clip = QPainterPath(); clip.addRoundedRect(screen, 12 / k, 12 / k); p.setClipPath(clip)
        paint_wallpaper(p, screen, self.wallpaper, self.colors.base, (110, 30, 120), self.colors.shade)
        # Superficie del mapa: sin la cabecera (~120 px) ni el dock y el pie (~185 px), como en el escritorio.
        surface = QRectF(42, 120, W - 78, H - 305)
        m = map_metrics(surface.width(), surface.height())
        cx, cy = surface.center().x(), surface.center().y()
        centre = QRectF(cx - m['cw'] / 2, cy - (m['nh'] + 8) / 2, m['cw'], m['nh'] + 8)
        cards = [QRectF(x - m['fw'] / 2, y - m['fh'] / 2, m['fw'], m['fh'])
                 for x, y in radial_slots(self.count, cx, cy, m['rx'], m['ry'])]
        visible = QPainterPath(); visible.addRect(screen)
        for card in [centre] + cards:
            hole = QPainterPath(); hole.addRoundedRect(card, 10, 10); visible = visible.subtracted(hole)
        p.setClipPath(visible.intersected(clip))
        pearl = QColor(self.colors.text)
        pearl.setAlpha(max(0, min(255, round(165 * self.traits.get('opacity', 1)))))
        for i, card in enumerate(cards):
            branch(p, centre.center(), card.center(), 7.5, 2.2, pearl, i, 5, traits=self.traits)
        p.setClipPath(clip)
        font = p.font(); font.setPixelSize(15); font.setBold(True); p.setFont(font)
        for card, text in [(centre, Path.cwd().name)] + [(c, 'Carpeta %d' % (i + 1)) for i, c in enumerate(cards)]:
            p.setPen(QPen(QColor(self.colors.border), 1.5)); p.setBrush(QColor(self.colors.panel))
            p.drawRoundedRect(card, 10, 10)
            p.setPen(QColor(self.colors.text)); p.drawText(card, Qt.AlignmentFlag.AlignCenter, text)
        # Cabecera y dock en silueta para situarse.
        font.setPixelSize(30); p.setFont(font); p.setPen(QColor(self.colors.text))
        p.drawText(QRectF(132, 44, W, 50), Qt.AlignmentFlag.AlignLeft, Path.cwd().name)
        p.setPen(QPen(QColor(self.colors.border), 1.5)); p.setBrush(QColor(self.colors.panel))
        p.drawRoundedRect(QRectF(42, H - 125, W - 78, 82), 14, 14)


class BranchSettings(QWidget):
    def __init__(self, folder=None):
        super().__init__()
        self.folder = Path(folder or Path.cwd())
        self.setWindowTitle('Ramas')
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry().height() if screen else 760
        self.resize(1000, max(560, min(820, available - 40)))
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

        layout = QVBoxLayout(self); layout.setContentsMargins(18, 12, 18, 18); layout.setSpacing(12)
        layout.addWidget(WindowHeader('Ramas para: {}'.format(self.folder.name), self))
        self.preview = Preview(self.wallpaper, self.colors)
        layout.addWidget(self.preview, 1)
        formats = QHBoxLayout()
        formats.addWidget(QLabel('Ver en pantalla'))
        self.aspect = QComboBox()
        ratio = screen_ratio()
        self.aspect.addItem('Esta pantalla (%.2f:1)' % ratio, ratio)
        for name, value in ASPECTS:
            self.aspect.addItem(name, value)
        self.aspect.currentIndexChanged.connect(lambda: (setattr(self.preview, 'ratio', self.aspect.currentData()), self.preview.update()))
        formats.addWidget(self.aspect); formats.addStretch(1)
        layout.addLayout(formats)

        saved = branch_style.raw(self.folder)
        self.auto = QCheckBox('Automático: el estilo sale del fondo')
        self.auto.setChecked(saved.get('auto', True))
        # Los controles van en una zona con desplazamiento: la ventana cabe en pantallas bajas (850 px)
        # aunque estén abiertos los dos gradientes.
        controls = QWidget(); body = QVBoxLayout(controls); body.setContentsMargins(4, 4, 14, 4); body.setSpacing(14)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(controls)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(scroll, 1)
        body.addWidget(self.auto)
        columns = QHBoxLayout(); columns.setSpacing(32); body.addLayout(columns)
        style_box = QVBoxLayout(); style_box.setSpacing(10); columns.addLayout(style_box, 1)
        style_box.addWidget(section('Estilo de la rama'))
        form = QFormLayout(); airy(form); style_box.addLayout(form); style_box.addStretch(1)
        self.sliders = {}
        for key, label in STYLE_LABELS:
            value = saved.get(key, self.auto_traits.get(key, .4 if key == 'detail' else 0))
            self.sliders[key] = self.slider(form, label, 0, 100, value * 100)
        for key, label in TWEAK_LABELS:
            low, high = branch_style.TWEAKS[key]
            self.sliders[key] = self.slider(form, label, round(low * 100), round(high * 100), saved.get(key, 1) * 100)
        # Gradiente de la rama, aparte del de los adornos.
        self.branch_form = form
        self.branch_gradient = QCheckBox('Gradiente en la rama')
        self.branch_gradient.setChecked(saved.get('branch_gradient') is True)
        form.addRow('', self.branch_gradient)
        self.branch_bars = {
            'opacity_end': self.value_slider(form, 'Opacidad al final', 0, 160, 100, '%'),
            'light': self.value_slider(form, 'Luz al principio', -100, 100, 100, ''),
            'light_end': self.value_slider(form, 'Luz al final', -100, 100, 100, '')}
        defaults = {'opacity_end': saved.get('opacity', 1), 'light': 0, 'light_end': 0}
        for key, slider in self.branch_bars.items():
            value = saved.get(key, defaults[key])
            slider.setValue(round((value if isinstance(value, (int, float)) else defaults[key]) * 100))
            slider.valueChanged.connect(self.update_preview)
        self.branch_gradient.toggled.connect(self.update_preview)
        columns.addLayout(self.build_ornaments(saved), 1)
        self.measured = QLabel(); self.measured.setObjectName('muted')
        body.addWidget(self.measured); body.addStretch(1)

        buttons = QHBoxLayout(); buttons.addStretch(1)
        for text, callback in (('Volver a automático', self.reset), ('Guardar en esta carpeta', self.save), ('Cerrar', self.close)):
            button = QPushButton(text); button.clicked.connect(callback); buttons.addWidget(button)
        layout.addLayout(buttons)
        self.auto.toggled.connect(self.update_preview)
        self.update_preview()

    def build_ornaments(self, saved):
        """Lista de adornos: cada uno con su frecuencia, sitio, tamaño y tinte."""
        box = QVBoxLayout(); box.setSpacing(10)
        box.addWidget(section('Adornos'))
        self.ornaments = []
        source = branch_style.settings_file(self.folder)
        for item in branch_style.clean({'ornaments': saved.get('ornaments', [])}, source.parent if source else None).get('ornaments', []):
            self.ornaments.append(item)
        self.ornament_list = QListWidget(); self.ornament_list.setIconSize(self.ornament_list.iconSize())
        self.ornament_list.currentRowChanged.connect(self.select_ornament)
        box.addWidget(self.ornament_list, 1)
        row = QHBoxLayout()
        add = QPushButton('Añadir adorno'); add.setObjectName('menuButton')
        menu = QMenu(add)
        for kind, label in BUILTIN_ORNAMENTS.items():
            menu.addAction(label, lambda kind=kind: self.add_ornament({'kind': kind}))
        menu.addSeparator()
        menu.addAction('Imagen propia…', self.add_image)
        add.setMenu(menu)
        remove = QPushButton('Quitar'); remove.clicked.connect(self.remove_ornament)
        row.addWidget(add); row.addWidget(remove); row.addStretch(1)
        box.addLayout(row)
        edit = QFormLayout(); airy(edit)
        self.bars, self.bars_end = {}, {}
        for key, label, low, high, scale, unit in ORNAMENT_BARS:
            self.bars[key] = self.value_slider(edit, label, low, high, scale, unit)
        self.side = self.combo(edit, 'Lado', SIDE_LABELS)
        self.order = self.combo(edit, 'Superposición', ORDER_LABELS)
        self.place = self.combo(edit, 'Dónde', PLACE_LABELS)
        self.gradient = QCheckBox('Gradiente: otro valor al final de la rama')
        edit.addRow('', self.gradient)
        for key, label, low, high, scale, unit in ORNAMENT_BARS[1:]:
            self.bars_end[key] = self.value_slider(edit, label + ' al final', low, high, scale, unit)
        self.tint = QCheckBox('Teñir con el color de las ramas')
        edit.addRow('', self.tint)
        box.addLayout(edit)
        self.edit_form = edit
        self.editors = list(self.bars.values()) + list(self.bars_end.values()) + [self.side, self.order, self.place, self.gradient, self.tint]
        for widget in self.editors:
            signal = widget.toggled if isinstance(widget, QCheckBox) else widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.valueChanged
            signal.connect(self.edit_ornament)
        self.refresh_ornaments()
        return box

    def value_slider(self, form, label, low, high, scale, unit):
        """Barra con su valor a la derecha."""
        row = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(low, high)
        value = QLabel(); value.setMinimumWidth(42)
        show = lambda v: value.setText(f'{v / scale:.2f}' if scale == 100 and not unit else f'{v}{unit}')
        slider.valueChanged.connect(show); show(slider.value())
        row.addWidget(slider, 1); row.addWidget(value)
        form.addRow(label, row)
        slider.scale, slider.show_value = scale, show
        return slider

    def combo(self, form, label, options):
        box = QComboBox()
        for key, text in options:
            box.addItem(text, key)
        form.addRow(label, box)
        return box

    def ornament_label(self, item):
        name = item['file'] if item['kind'] == 'imagen' else BUILTIN_ORNAMENTS[item['kind']]
        frequency = 'nunca' if item['density'] <= 0 else f"frecuencia {item['density']:.2f}"
        return f"{name} · {frequency} · {item['angle']:.0f}° {dict(SIDE_LABELS)[item['side']].split(',')[0].lower()}"

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
        for widget in self.editors:
            widget.setEnabled(editing); widget.blockSignals(True)
        if editing:
            item = self.ornaments[row]
            for key, slider in self.bars.items():
                slider.setValue(round(item[key] * slider.scale))
            gradient = any(item[key + '_end'] != item[key] for key in self.bars_end)
            for key, slider in self.bars_end.items():
                slider.setValue(round(item[key + '_end'] * slider.scale))
            self.gradient.setChecked(gradient)
            for box, key in ((self.side, 'side'), (self.order, 'order'), (self.place, 'place')):
                box.setCurrentIndex(box.findData(item[key]))
            self.tint.setChecked(item['tint'])
        for widget in self.editors:
            widget.blockSignals(False)
        self.show_gradient(editing and self.gradient.isChecked())
        # Con las señales bloqueadas las etiquetas de valor no se enteran: se refrescan a mano.
        for slider in list(self.bars.values()) + list(self.bars_end.values()):
            slider.show_value(slider.value())

    def show_gradient(self, visible):
        """Las barras «al final» solo ocupan sitio con el gradiente activado."""
        for slider in self.bars_end.values():
            row = self.row_of(slider)
            if row >= 0:
                self.edit_form.setRowVisible(row, visible)

    def row_of(self, slider):
        return self.row_in(self.edit_form, slider)

    @staticmethod
    def row_in(form, slider):
        for row in range(form.rowCount()):
            field = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
            if field and field.layout() and field.layout().indexOf(slider) >= 0:
                return row
        return -1

    def edit_ornament(self, *_):
        row = self.ornament_list.currentRow()
        if not 0 <= row < len(self.ornaments):
            return
        item = self.ornaments[row]
        for key, slider in self.bars.items():
            item[key] = slider.value() / slider.scale
        gradient = self.gradient.isChecked()
        self.show_gradient(gradient)
        for key, slider in self.bars_end.items():
            item[key + '_end'] = slider.value() / slider.scale if gradient else item[key]
        item.update(side=self.side.currentData(), order=self.order.currentData(), place=self.place.currentData(),
                    tint=self.tint.isChecked())
        self.ornament_list.item(row).setText(self.ornament_label(item))
        self.update_preview()

    def add_ornament(self, item):
        if len(self.ornaments) >= branch_style.MAX_ORNAMENTS:
            QMessageBox.information(self, 'Adornos', 'Como mucho %d adornos.' % branch_style.MAX_ORNAMENTS); return
        item = branch_style.clean({'ornaments': [{'density': .3, 'angle': 45, **item}]}, self.folder)['ornaments'][0] \
            if item.get('kind') != 'imagen' else {**branch_style.clean({'ornaments': [{'kind': 'seta'}]})['ornaments'][0], **item}
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
        if hasattr(self, 'branch_gradient'):
            data['branch_gradient'] = self.branch_gradient.isChecked()
            for key, slider in self.branch_bars.items():
                data[key] = round(slider.value() / 100, 2)
        data['ornaments'] = []
        for item in getattr(self, 'ornaments', []):
            entry = {key: value for key, value in item.items() if key not in ('path', 'file')}
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
        if hasattr(self, 'branch_bars'):
            for slider in self.branch_bars.values():
                row = self.row_in(self.branch_form, slider)
                if row >= 0:
                    self.branch_form.setRowVisible(row, self.branch_gradient.isChecked())
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
    from .appearance import speak_spanish; speak_spanish(app)
    window = BranchSettings()
    window.show()
    if '--screenshot' in sys.argv:
        from PySide6.QtCore import QTimer
        target = sys.argv[sys.argv.index('--screenshot') + 1]
        QTimer.singleShot(400, lambda: (window.grab().save(target), app.quit()))
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
