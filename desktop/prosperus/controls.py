"""Explicit volume, playback and backlight controls for the current Linux session."""
# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import shutil

from PySide6.QtCore import QObject, QProcess, Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

COMMANDS = {
    'volume-up': ('wpctl', ['set-volume', '@DEFAULT_AUDIO_SINK@', '5%+', '--limit', '1.0']),
    'volume-down': ('wpctl', ['set-volume', '@DEFAULT_AUDIO_SINK@', '5%-']),
    'mute': ('wpctl', ['set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle']),
    'brightness-up': ('brightnessctl', ['--class=backlight', 'set', '+5%']),
    'brightness-down': ('brightnessctl', ['--class=backlight', '--min-value=1', 'set', '5%-']),
    'play-pause': ('playerctl', ['play-pause']),
    'next': ('playerctl', ['next']),
    'previous': ('playerctl', ['previous']),
    'stop': ('playerctl', ['stop']),
}
MEDIA_KEYS = {
    Qt.Key.Key_VolumeUp: 'volume-up', Qt.Key.Key_VolumeDown: 'volume-down',
    Qt.Key.Key_VolumeMute: 'mute', Qt.Key.Key_MonBrightnessUp: 'brightness-up',
    Qt.Key.Key_MonBrightnessDown: 'brightness-down', Qt.Key.Key_MediaPlay: 'play-pause',
    Qt.Key.Key_MediaTogglePlayPause: 'play-pause', Qt.Key.Key_MediaNext: 'next',
    Qt.Key.Key_MediaPrevious: 'previous', Qt.Key.Key_MediaStop: 'stop',
}


class SessionControls(QObject):
    message = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(lambda _: self.message.emit(self.process.errorString()))
        self.action = ''

    def available(self, action):
        command = COMMANDS.get(action)
        if command is None or not shutil.which(command[0]):
            return False
        if action.startswith('brightness'):
            return any(Path('/sys/class/backlight').glob('*'))
        return True

    def execute(self, action):
        if not self.available(action):
            self.message.emit('Este control no está disponible en la sesión o el dispositivo actual.'); return
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self.action = action
        program, arguments = COMMANDS[action]
        self.process.start(program, arguments)

    def finished(self, code, status):
        error = bytes(self.process.readAllStandardError()).decode('utf-8', errors='replace').strip()
        self.message.emit('Control aplicado.' if not code and status == QProcess.ExitStatus.NormalExit else error or 'No se pudo aplicar el control.')

    def handle_key(self, key):
        action = MEDIA_KEYS.get(key)
        if action:
            self.execute(action)
            return True
        return False


class ControlsDialog(QDialog):
    def __init__(self, shell):
        super().__init__(shell)
        self.setWindowTitle('Controles del escritorio'); self.resize(520, 300)
        layout = QVBoxLayout(self)
        for title, actions in [
            ('Volumen', [('−', 'volume-down'), ('Silenciar', 'mute'), ('+', 'volume-up')]),
            ('Reproducción', [('Anterior', 'previous'), ('Reproducir / pausa', 'play-pause'), ('Siguiente', 'next')]),
            ('Brillo', [('−', 'brightness-down'), ('+', 'brightness-up')]),
        ]:
            row = QHBoxLayout(); row.addWidget(QLabel(title), 1)
            for text, action in actions:
                control = QPushButton(text); control.setEnabled(shell.controls.available(action))
                control.clicked.connect(lambda checked=False, a=action: shell.controls.execute(a)); row.addWidget(control)
            layout.addLayout(row)
        status = QLabel('Los controles actúan en el sistema donde se ejecuta PrOSperus. El brillo requiere una pantalla compatible; normalmente no está disponible en una VM.')
        status.setWordWrap(True); layout.addWidget(status)
        shell.controls.message.connect(status.setText)
        self.finished.connect(lambda: shell.controls.message.disconnect(status.setText))
        close = QPushButton('Cerrar'); close.clicked.connect(self.accept); layout.addWidget(close)
