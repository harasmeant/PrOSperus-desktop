"""Explicit volume, playback and backlight controls for the current Linux session."""
# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import shutil

from PySide6.QtCore import QObject, QProcess, Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .incoming import DestinationsDialog

# Mapeo de acciones a programas y argumentos del sistema.
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
# Mapeo de teclas multimedia Qt a acciones.
MEDIA_KEYS = {
    Qt.Key.Key_VolumeUp: 'volume-up', Qt.Key.Key_VolumeDown: 'volume-down',
    Qt.Key.Key_VolumeMute: 'mute', Qt.Key.Key_MonBrightnessUp: 'brightness-up',
    Qt.Key.Key_MonBrightnessDown: 'brightness-down', Qt.Key.Key_MediaPlay: 'play-pause',
    Qt.Key.Key_MediaTogglePlayPause: 'play-pause', Qt.Key.Key_MediaNext: 'next',
    Qt.Key.Key_MediaPrevious: 'previous', Qt.Key.Key_MediaStop: 'stop',
}

# Controlador de sesiones para acciones de volumen, brillo y medios a través de wpctl/brightnessctl/playerctl.
class SessionControls(QObject):
    # Señal que emite mensajes al UI.
    message = Signal(str)

    # Inicializa el controlador: configura QProcess y gestiona señales.
    def __init__(self, parent=None):
        super().__init__(parent)
        # Proceso del sistema para ejecutar comandos externos.
        self.process = QProcess(self)
        # Conectar finalización del proceso.
        self.process.finished.connect(self.finished)
        # Emitir error si ocurre un fallo en QProcess.
        self.process.errorOccurred.connect(lambda _: self.message.emit(self.process.errorString()))
        # Última acción ejecutada (útil para depuración).
        self.action = ''

    # Comprueba si una acción está disponible (comando existe y, para brillo, hay pantalla).
    def available(self, action):
        command = COMMANDS.get(action)
        if command is None or not shutil.which(command[0]):
            return False
        # Para controles de brillo, verificar la existencia de al menos una interfaz de retroiluminación.
        if action.startswith('brightness'):
            return any(Path('/sys/class/backlight').glob('*'))
        return True

    # Ejecuta la acción: verifica disponibilidad, evita procesos concurrentes, inicia QProcess.
    def execute(self, action):
        if not self.available(action):
            self.message.emit('Este control no está disponible en la sesión o el dispositivo actual.')
            return
        # No iniciar un nuevo proceso si uno ya está en ejecución.
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self.action = action
        program, arguments = COMMANDS[action]
        self.process.start(program, arguments)

    # Manejador de finalización del proceso: informa de éxito o error.
    def finished(self, code, status):
        error = bytes(self.process.readAllStandardError()).decode('utf-8', errors='replace').strip()
        self.message.emit('Control aplicado.' if not code and status == QProcess.ExitStatus.NormalExit else error or 'No se pudo aplicar el control.')

    # Convierte una tecla Qt en acción y ejecuta la correspondiente (si existe).
    def handle_key(self, key):
        action = MEDIA_KEYS.get(key)
        if action:
            self.execute(action)
            return True
        return False


# Diálogo de UI que presenta controles de volumen, reproducción y brillo como botones.
class ControlsDialog(QDialog):
    # Construye la interfaz: botones para distribución, accesibilidad, drivers, controles de volumen/reproducción/brillo.
    def __init__(self, shell):
        super().__init__(shell)
        self.setWindowTitle('Controles del escritorio'); self.resize(520, 300)
        layout = QVBoxLayout(self)

        # Botón para abrir ajustes de pantalla y distribución del escritorio.
        distribution = QPushButton('Pantallas y distribución…')
        distribution.clicked.connect(shell.open_layout_settings)
        layout.addWidget(distribution)
        monitors = QPushButton('Monitores (extender, duplicar)…')
        monitors.clicked.connect(shell.open_display_settings)
        layout.addWidget(monitors)

        # Botones para abrir ajustes generales del sistema (accesibilidad y drivers).
        for title, action in [('Accesibilidad y botones…', shell.open_accessibility),
                              ('Hardware y drivers…', shell.open_hardware),
                              ('Destinos de archivos…', lambda: DestinationsDialog(self).exec())]:
            option = QPushButton(title); option.clicked.connect(action); layout.addWidget(option)

        # Crea filas de controles (volumen, reproducción, brillo) con botones habilitados/deshabilitados según disponibilidad.
        for title, actions in [
            ('Volumen', [('− Bajar volumen', 'volume-down'), ('Silenciar / activar sonido', 'mute'), ('+ Subir volumen', 'volume-up')]),
            ('Reproducción', [('⏮ Anterior', 'previous'), ('▶ Reproducir / pausa', 'play-pause'), ('⏭ Siguiente', 'next')]),
            ('Brillo', [('− Bajar brillo', 'brightness-down'), ('+ Subir brillo', 'brightness-up')]),
        ]:
            # Fila horizontal para los controles de un grupo.
            row = QHBoxLayout(); row.addWidget(QLabel(title), 1)
            # Crea un botón para cada acción; habilita solo si disponible.
            for text, action in actions:
                control = QPushButton(text); control.setEnabled(shell.controls.available(action))
                # Eliminar símbolos de atajo para el nombre accesible.
                control.setAccessibleName(text.lstrip('−+⏮▶⏭ '))
                # Si el botón está deshabilitado, mostrar un tooltip explicativo.
                control.setToolTip(control.accessibleName() if control.isEnabled() else
                                   'No disponible: falta la herramienta de sesión o un dispositivo compatible.')
                # Conectar el clic; la lambda captura el valor actual de 'action'.
                control.clicked.connect(lambda checked=False, a=action: shell.controls.execute(a))
                row.addWidget(control)
            layout.addLayout(row)

        # Etiqueta informativa sobre el comportamiento del brillo y el sistema.
        status = QLabel('Los controles actúan en el sistema donde se ejecuta PrOSperus. El brillo requiere una pantalla compatible; normalmente no está disponible en una VM.')
        status.setWordWrap(True); layout.addWidget(status)

        # Actualiza la etiqueta con los mensajes del controlador; limpia al cerrar el diálogo.
        shell.controls.message.connect(status.setText)
        self.finished.connect(lambda: shell.controls.message.disconnect(status.setText))

        # Botón para cerrar el diálogo.
        close = QPushButton('Cerrar'); close.clicked.connect(self.accept); layout.addWidget(close)
