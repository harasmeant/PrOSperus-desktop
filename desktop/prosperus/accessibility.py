"""User preferences shared by native widgets and the painted desktop."""
# SPDX-License-Identifier: GPL-3.0-only
from dataclasses import dataclass
import re

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout,
                              QLabel, QPushButton, QVBoxLayout)


# Clase de datos inmutable que almacena preferencias de accesibilidad.
@dataclass(frozen=True)
class Accessibility:
    text_scale: int = 100
    large_buttons: bool = False
    high_contrast: bool = False
    single_click: bool = False

    # Carga la configuración de accesibilidad desde QSettings, validando valores seguros
    # y aplicando defaults (100) si los valores son inválidos o no están en la lista permitida.
    @classmethod
    def load(cls, settings):
        try:
            scale = int(settings.value('accessibility/text_scale', 100))
        except (ValueError, TypeError):
            scale = 100
        def flag(name):
            return str(settings.value('accessibility/' + name, 'false')).lower() in ('true', '1')
        return cls(scale if scale in (100, 125, 150) else 100,
                   flag('large_buttons'), flag('high_contrast'), flag('single_click'))

    # Guarda la configuración actual en QSettings y síncroniza con el archivo de configuración.
    # Devuelve True si el estado de escritura es NoError.
    def save(self, settings):
        for key, value in vars(self).items():
            settings.setValue('accessibility/' + key, value)
        settings.sync()
        return settings.status() == QSettings.Status.NoError

    # Escala el tamaño de fuente proporcionalmente al factor text_scale, redondeando al entero.
    def font_size(self, points):
        return round(points * self.text_scale / 100)

    # Ajusta los colores del palette a alto contraste si está activado, dejando pasar si no.
    def palette(self, palette):
        if self.high_contrast:
            palette.base = palette.panel = palette.card = '#000000'
            palette.hover = '#242424'
            palette.text = palette.muted = '#ffffff'
            palette.accent = '#ffff00'
            palette.border = '#ffffff'
        return palette

    # Genera CSS personalizado modificando tamaños de fuente y estilos de enfoque/selección
    # según la configuración de accesibilidad (tamaño grande, botones grandes, contraste).
    def css(self, palette):
        css = re.sub(r'font-size: (\d+)px',
                     lambda m: f'font-size: {self.font_size(int(m[1]))}px', palette.css())
        # Foco visible pero suave; en notas y editores basta el cursor (el marco tapaba el texto).
        # Con alto contraste, todo lleva el marco grueso.
        boxes = 'QLineEdit:focus, QListWidget:focus, QComboBox:focus, QSpinBox:focus, QCheckBox:focus'
        if self.high_contrast:
            boxes += ', QPlainTextEdit:focus, QTextBrowser:focus'
        css += '''
        %s {
            border: %s solid %s;
        }
        QListWidget::item:selected { background: %s; color: %s; }
        ''' % (boxes, '2px' if self.high_contrast else '1px', palette.accent, palette.hover, palette.text)
        if self.large_buttons:
            css += 'QPushButton { min-height: 30px; padding: 12px 20px; }'
        return css


# Diálogo configurador de accesibilidad con controles de interfaz de usuario,
# vinculado al shell para aplicar cambios en tiempo real.
class AccessibilityDialog(QDialog):
    # Inicializa el diálogo, crea los controles de formulario (combinación, casillas)
    # y los enlaza con la configuración actual del shell.
    def __init__(self, shell):
        super().__init__(shell)
        self.shell = shell
        self.setWindowTitle('Accesibilidad y botones'); self.resize(550, 350)
        layout = QVBoxLayout(self)
        form = QFormLayout(); layout.addLayout(form)
        self.scale = QComboBox()
        for value in (100, 125, 150):
            self.scale.addItem(f'{value} %', value)
        self.scale.setCurrentIndex(self.scale.findData(shell.accessibility.text_scale))
        form.addRow('Tamaño del texto', self.scale)
        self.large = QCheckBox('Botones grandes')
        self.contrast = QCheckBox('Alto contraste (sin fondos de imagen)')
        self.single = QCheckBox('Abrir notas y carpetas con un clic')
        for control, value in ((self.large, shell.accessibility.large_buttons),
                               (self.contrast, shell.accessibility.high_contrast),
                               (self.single, shell.accessibility.single_click)):
            control.setChecked(value); layout.addWidget(control)
        hint = QLabel('Tab y Mayús+Tab recorren los controles; Espacio activa botones. '
                      'Con clic simple, Ctrl+clic permite seleccionar sin abrir. '
                      'Los ajustes se aplican a PrOSperus y se guardan para este usuario.')
        hint.setWordWrap(True); layout.addWidget(hint)
        self.status = QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        apply = QPushButton('Aplicar y guardar'); apply.clicked.connect(self.apply); layout.addWidget(apply)
        close = QPushButton('Cerrar'); close.clicked.connect(self.accept); layout.addWidget(close)

    # Aplica y guarda la nueva configuración de accesibilidad en el shell,
    # actualiza el atributo de acceso y muestra un mensaje de estado.
    def apply(self):
        options = Accessibility(self.scale.currentData(), self.large.isChecked(),
                                self.contrast.isChecked(), self.single.isChecked())
        if not options.save(self.shell.settings):
            self.status.setText('No se pudieron guardar los ajustes.'); return
        self.shell.accessibility = options
        self.shell.apply_accessibility()
        self.status.setText('Ajustes aplicados y guardados.')
