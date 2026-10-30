"""Ajustes de distribución por tipo de pantalla, con vista previa antes de aplicar."""
# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import os
import sys

from PySide6.QtCore import QProcess, QRectF, QSettings, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFormLayout,
    QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget)
from .window_layouts import LayoutOptions, Rect, arrange, screen_profile

PROFILES = [('standard', 'Pantalla estándar'), ('ultrawide', 'Ultrawide · 21:9'),
            ('superwide', 'Superultrawide · 32:9')]
MODES = [('spiral', 'Espiral Fibonacci'), ('columns', 'Columnas'),
         ('centered', 'Principal centrada')]


class LayoutPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.setAccessibleName('Vista previa de la distribución de ventanas')
        self.area = Rect(0, 0, 1920, 1080)
        self.options = LayoutOptions()
        self.count = 4

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        factor = min((self.width() - 16) / self.area.width, (self.height() - 16) / self.area.height)
        painter.translate((self.width() - self.area.width * factor) / 2,
                          (self.height() - self.area.height * factor) / 2)
        painter.scale(factor, factor)
        painter.fillRect(QRectF(0, 0, self.area.width, self.area.height), QColor('#10181e'))
        try:
            boxes = arrange(self.area, self.count, self.options)
        except ValueError:
            return
        for i, r in enumerate(boxes):
            rect = QRectF(r.x, r.y, r.width, r.height)
            painter.setPen(QColor('#9bc8be'))
            painter.setBrush(QColor('#325149' if i == 0 else '#26353e'))
            painter.drawRoundedRect(rect, 8 / factor, 8 / factor)
            font = painter.font(); font.setPointSizeF(10 / factor); painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, 'Principal' if i == 0 else str(i + 1))


class LayoutDialog(QDialog):
    def __init__(self, shell, settings=None):
        super().__init__(shell)
        self.shell = shell
        self.settings = settings if settings is not None else QSettings('PrOSperus', 'Desktop')
        self.previous = {}
        self.setWindowTitle('Pantallas y distribución'); self.resize(690, 650)
        layout = QVBoxLayout(self)
        intro = QLabel('Organiza el espacio de trabajo y guarda ajustes para cada tipo de pantalla.')
        intro.setWordWrap(True); layout.addWidget(intro)
        form = QFormLayout(); layout.addLayout(form)
        self.screen_choice = QComboBox(); form.addRow('Pantalla', self.screen_choice)
        self.screen_info = QLabel(); self.screen_info.setWordWrap(True); form.addRow('', self.screen_info)
        self.profile = QComboBox()
        for identity, title in PROFILES:
            self.profile.addItem(title, identity)
        form.addRow('Perfil', self.profile)
        self.mode = QComboBox()
        for identity, title in MODES:
            self.mode.addItem(title, identity)
        form.addRow('Distribución', self.mode)
        self.gap = QSpinBox(); self.gap.setRange(0, 48); self.gap.setSuffix(' px lógicos')
        self.ratio = QSpinBox(); self.ratio.setRange(30, 70); self.ratio.setSuffix(' %')
        self.width_limit = QSpinBox(); self.width_limit.setRange(0, 10000)
        self.width_limit.setSingleStep(100); self.width_limit.setSpecialValueText('Toda la anchura')
        self.width_limit.setSuffix(' px lógicos')
        self.count = QSpinBox(); self.count.setRange(1, 12); self.count.setValue(4)
        for title, widget in [('Separación', self.gap), ('Ventana principal', self.ratio),
                              ('Anchura centrada máxima', self.width_limit), ('Ventanas en la vista previa', self.count)]:
            form.addRow(title, widget)
        self.preview = LayoutPreview(); layout.addWidget(self.preview, 1)
        self.preview_status = QLabel(); self.preview_status.setWordWrap(True); layout.addWidget(self.preview_status)
        self.status = QLabel('Los ajustes se guardan en este usuario. No cambian la resolución ni la escala del monitor.')
        self.status.setWordWrap(True); layout.addWidget(self.status)
        row = QHBoxLayout(); layout.addLayout(row)
        save = QPushButton('Guardar perfil'); save.clicked.connect(self.save_profile); row.addWidget(save)
        notes = QPushButton('Organizar notas'); notes.clicked.connect(self.apply_notes); row.addWidget(notes)
        self.undo = QPushButton('Deshacer notas'); self.undo.setEnabled(False)
        self.undo.clicked.connect(self.undo_notes); row.addWidget(self.undo)
        self.external = QPushButton('Organizar aplicaciones'); row.addWidget(self.external)
        self.external.setEnabled(bool(os.environ.get('SWAYSOCK')))
        self.external.setToolTip('Disponible en la sesión experimental con Sway; organiza el espacio visible de la pantalla elegida.')
        self.external.clicked.connect(self.apply_applications)
        if not self.external.isEnabled():
            hint = QLabel('Esta sesión aún no permite distribuir ventanas de aplicaciones externas.')
            hint.setWordWrap(True); layout.addWidget(hint)
        close = QPushButton('Cerrar'); close.clicked.connect(self.accept); layout.addWidget(close)
        self.process = QProcess(self)
        self.process.finished.connect(self.application_result)
        self.process.errorOccurred.connect(lambda _: self.status.setText(self.process.errorString()))
        self.profile.currentIndexChanged.connect(self.load_profile)
        self.screen_choice.currentIndexChanged.connect(self.select_screen)
        for widget in (self.mode,):
            widget.currentIndexChanged.connect(self.refresh_preview)
        for widget in (self.gap, self.ratio, self.width_limit, self.count):
            widget.valueChanged.connect(self.refresh_preview)
        QApplication.instance().screenAdded.connect(self.reload_screens)
        QApplication.instance().screenRemoved.connect(self.reload_screens)
        self.finished.connect(self.detach)
        self.reload_screens()

    def detach(self):
        QApplication.instance().screenAdded.disconnect(self.reload_screens)
        QApplication.instance().screenRemoved.disconnect(self.reload_screens)

    def reload_screens(self, *_):
        previous = self.screen_choice.currentData()
        self.screen_choice.blockSignals(True); self.screen_choice.clear()
        for screen in QApplication.screens():
            self.screen_choice.addItem(screen.name() or 'Pantalla principal', screen.name())
        preferred = previous if previous is not None else self.shell.screen().name()
        self.screen_choice.setCurrentIndex(max(0, self.screen_choice.findData(preferred)))
        self.screen_choice.blockSignals(False); self.select_screen()

    def selected_screen(self):
        return next((s for s in QApplication.screens() if s.name() == self.screen_choice.currentData()), None)

    def screen_key(self):
        return hashlib.sha256(str(self.screen_choice.currentData()).encode()).hexdigest()[:16]

    def select_screen(self, *_):
        screen = self.selected_screen()
        if screen is None:
            self.status.setText('No hay pantallas disponibles.'); return
        size = screen.availableGeometry()
        self.screen_info.setText(f'{size.width()} × {size.height()} lógicos · escala {screen.devicePixelRatio():g}× · {screen.refreshRate():.0f} Hz')
        detected = screen_profile(size.width(), size.height())
        selected = self.settings.value('layouts/screens/' + self.screen_key(), detected)
        self.profile.blockSignals(True)
        self.profile.setCurrentIndex(max(0, self.profile.findData(selected)))
        self.profile.blockSignals(False); self.load_profile()

    def load_profile(self, *_):
        prefix = 'layouts/profiles/' + self.profile.currentData() + '/'
        mode = self.settings.value(prefix + 'mode', 'spiral')
        try:
            values = [int(self.settings.value(prefix + key, default))
                      for key, default in [('gap', 12), ('ratio', 50), ('max_width', 0)]]
            options = LayoutOptions(mode, *values); options.validate()
        except (TypeError, ValueError):
            options = LayoutOptions()
        self.mode.setCurrentIndex(self.mode.findData(options.mode))
        self.gap.setValue(options.gap); self.ratio.setValue(options.ratio)
        self.width_limit.setValue(options.max_width); self.refresh_preview()

    def options(self):
        return LayoutOptions(self.mode.currentData(), self.gap.value(), self.ratio.value(), self.width_limit.value())

    def refresh_preview(self, *_):
        screen = self.selected_screen()
        if screen is None:
            return
        size = screen.availableGeometry()
        self.preview.area = Rect(0, 0, size.width(), size.height())
        self.preview.options = self.options(); self.preview.count = self.count.value()
        try:
            arrange(self.preview.area, self.preview.count, self.options())
            message = 'Vista previa de la pantalla. Las notas usan el área del mapa; las aplicaciones, el espacio visible.'
        except ValueError as error:
            message = str(error)
        self.preview_status.setText(message); self.preview.update()
        self.ratio.setEnabled(self.mode.currentData() != 'columns')

    def save_profile(self):
        prefix = 'layouts/profiles/' + self.profile.currentData() + '/'
        for key, value in vars(self.options()).items():
            self.settings.setValue(prefix + key, value)
        self.settings.setValue('layouts/screens/' + self.screen_key(), self.profile.currentData())
        self.settings.sync()
        self.status.setText('Perfil guardado.' if self.settings.status() == QSettings.Status.NoError else 'No se pudo guardar el perfil.')

    def apply_notes(self):
        if self.selected_screen() != self.shell.screen():
            self.status.setText('Mueve PrOSperus a esa pantalla para organizar sus notas.'); return
        panels = [p for p in self.shell.panels.values() if p.isVisible() and not p.minimized]
        if not panels:
            self.status.setText('Abre notas en el proyecto para organizarlas.'); return
        area = self.shell.surface.rect()
        try:
            boxes = arrange(Rect(0, 0, area.width(), area.height()), len(panels), self.options(),
                            (max(p.minimumWidth() for p in panels), max(p.minimumHeight() for p in panels)))
        except ValueError as error:
            self.status.setText(str(error)); return
        self.previous = {p.path: p.geometry() for p in panels}
        for panel, box in zip(panels, boxes):
            panel.setGeometry(box.x, box.y, box.width, box.height)
        self.undo.setEnabled(True); self.status.setText(f'{len(panels)} notas organizadas. Puedes deshacer esta distribución.')

    def undo_notes(self):
        for path, geometry in self.previous.items():
            panel = self.shell.panels.get(path)
            if panel is not None:
                panel.setGeometry(geometry)
        self.previous = {}; self.undo.setEnabled(False); self.status.setText('Distribución anterior recuperada.')

    def apply_applications(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        output = self.screen_choice.currentData()
        if output is None:
            return
        options = self.options()
        self.status.setText('Organizando aplicaciones de la pantalla seleccionada…')
        self.process.start(sys.executable, ['-m', 'prosperus.window_session', '--output', output,
            '--mode', options.mode, '--gap', str(options.gap), '--ratio', str(options.ratio),
            '--max-width', str(options.max_width)])

    def application_result(self, code, status):
        success = code == 0 and status == QProcess.ExitStatus.NormalExit
        message = bytes(self.process.readAllStandardOutput() if success else self.process.readAllStandardError()).decode(errors='replace')
        self.status.setText(message.strip() or 'No se pudo completar la distribución.')

    def done(self, result):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.status.setText('Espera a que termine la distribución de aplicaciones.'); return
        super().done(result)
