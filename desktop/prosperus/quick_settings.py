# SPDX-License-Identifier: GPL-3.0-only
"""Panel rápido de la esquina derecha: brillo, volumen, wifi, bluetooth y notificaciones."""
import os
import subprocess
import sys
import threading
from .appearance import arrow
from PySide6.QtWidgets import (QComboBox, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QSlider, QPushButton, QWidget)
from PySide6.QtCore import QProcess, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from .branches import flourish
from .focus_trap import cycle_focus

def run(argv):
    """Ejecuta un comando sin shell y captura la salida (None si falla)."""
    return attempt(argv)[1]


def attempt(argv):
    """(correcto, salida o motivo del fallo). Los fallos quedan en el registro del sistema
    (la salida del escritorio va al journal) para poder diagnosticar en el equipo real."""
    try:
        res = subprocess.run(argv, timeout=3, capture_output=True, text=True, check=True)
        return True, res.stdout.strip()
    except subprocess.CalledProcessError as error:
        reason = (error.stderr or error.stdout or '').strip() or f'código {error.returncode}'
    except FileNotFoundError:
        reason = 'no está instalado'
    except (subprocess.SubprocessError, OSError) as error:
        reason = str(error)
    print(f'prosperus-panel: {" ".join(argv)}: {reason}', file=sys.stderr, flush=True)
    return False, None

def parse_volume(text):
    """Parsea salida de wpctl: 'Volume: 0.40 [MUTED]' -> (40, True)."""
    if not text or "Volume:" not in text: return None
    try:
        muted = "[MUTED]" in text
        val = float(text.split("Volume:")[1].split("[")[0].strip())
        return round(val * 100), muted
    except (ValueError, IndexError): return None

def parse_brightness(text):
    """Parsea salida de brightnessctl -m."""
    if not text: return None
    try: return int(text.split(",")[3].replace("%", ""))
    except (ValueError, IndexError): return None


def parse_sinks(text):
    """Salidas de sonido de `wpctl status`: [(id, nombre, es_la_actual)]. Solo la sección Audio.
    Base de qwen2.5-coder (local); corregido que los títulos llevan delante «├─»."""
    import re
    if not text:
        return []
    in_audio = in_sinks = False
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == 'Audio':
            in_audio = True
        elif stripped in ('Video', 'Settings'):
            in_audio = in_sinks = False
        elif in_audio and stripped.endswith('Sinks:'):
            in_sinks = True
        elif in_audio and stripped.endswith(('Sources:', 'Filters:', 'Streams:', 'Devices:')):
            in_sinks = False
        elif in_sinks:
            match = re.search(r'(\*)?\s+(\d+)\.\s+(.+?)(?:\s+\[vol:.*\])?\s*$', line)
            if match:
                star, number, name = match.groups()
                result.append((int(number), name.strip(), star is not None))
    return result


def parse_track(text):
    """`playerctl metadata --format '{{status}}|{{artist}}|{{title}}'` -> (sonando, 'Artista · Título')."""
    if not text or '|' not in text:
        return None
    status, artist, title = (text.split('|', 2) + ['', ''])[:3]
    label = ' · '.join(part for part in (artist.strip(), title.strip()) if part) or 'Sin título'
    return status.strip() == 'Playing', label


def parse_powered(text):
    """Parsea salida de bluetoothctl show."""
    if not text: return None
    for line in text.splitlines():
        if line.strip().startswith("Powered:"):
            return line.split(":", 1)[1].strip() == "yes"
    return None

def terminal(argv):
    """Abre una herramienta de texto (nmtui, bluetoothctl) en la consola."""
    QProcess.startDetached('prosperus-terminal', argv)


class QuickSettings(QFrame):
    state_ready = Signal(dict)

    # Ajustes de sistema rápidos
    def __init__(self, shell):
        super().__init__()
        self.state_ready.connect(self.apply)
        self.setMinimumWidth(420)
        self.restyle(shell.colors)
        self.shell = shell
        self.setObjectName("quickSettings")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(24, 22, 24, 22)
        self.box.setSpacing(10)
        
        # 1. Brillo
        self.br_row = QHBoxLayout()
        self.br_lbl = self.section("Brillo", first=True)
        self.br_value = QLabel(objectName="value")
        self.brightness = QSlider(Qt.Horizontal)
        self.brightness.setRange(5, 100)
        # Se aplica al moverla de cualquier forma (arrastrar, clic, rueda, flechas), con un pequeño
        # retardo para no lanzar una orden por cada píxel.
        self.br_timer = QTimer(self, singleShot=True, interval=120, timeout=self._set_br)
        self.brightness.valueChanged.connect(lambda _: self.br_timer.start())
        self.brightness.valueChanged.connect(lambda v: self.br_value.setText(f'{v} %'))
        self.br_err = QLabel("Esta pantalla no permite cambiar el brillo.", objectName="hint", wordWrap=True)
        self.br_err.hide()
        self.br_row.addWidget(self.brightness, 1)
        self.br_row.addWidget(self.br_value)
        self.box.addLayout(self.br_row)
        self.box.addWidget(self.br_err)

        # 2. Volumen
        self.vol_row = QHBoxLayout()
        self.vol_lbl = self.section("Volumen")
        self.vol_value = QLabel(objectName="value")
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.vol_timer = QTimer(self, singleShot=True, interval=120, timeout=self._set_vol)
        self.volume.valueChanged.connect(lambda _: self.vol_timer.start())
        self.volume.valueChanged.connect(lambda v: self.vol_value.setText(f'{v} %'))
        self.mute = QPushButton("Silencio")
        self.mute.setCheckable(True)
        self.mute.clicked.connect(self._set_mute)
        self.vol_err = QLabel("Sin salida de sonido.", objectName="hint", wordWrap=True)
        self.vol_err.hide()
        self.vol_row.addWidget(self.volume, 1)
        self.vol_row.addWidget(self.vol_value)
        self.vol_row.addWidget(self.mute)
        self.box.addLayout(self.vol_row)
        self.box.addWidget(self.vol_err)
        # Salida de sonido (altavoces, HDMI, auriculares…): la elegida pasa a ser la predeterminada.
        self.sink = QComboBox()
        self.sink.activated.connect(self._set_sink)
        self.box.addWidget(self.sink)

        # Reproducción (playerctl: navegador, Spotify, VLC…): solo se ve si hay algo sonando o en pausa.
        self.media = QWidget()
        media_row = QHBoxLayout(self.media); media_row.setContentsMargins(0, 0, 0, 0)
        self.track = QLabel(objectName='value'); self.track.setWordWrap(True)
        self.play = QPushButton('⏯')
        for text, action in (('⏮', 'previous'), (None, 'play-pause'), ('⏭', 'next')):
            button = self.play if text is None else QPushButton(text)
            button.setObjectName('media')
            button.setToolTip({'previous': 'Anterior', 'play-pause': 'Reproducir / pausa', 'next': 'Siguiente'}[action])
            button.clicked.connect(lambda _=False, a=action: (run(['playerctl', a]), QTimer.singleShot(300, self.refresh)))
            media_row.addWidget(button)
        media_row.addWidget(self.track, 1)
        self.media_title = self.section('Reproduciendo')
        self.box.addWidget(self.media)
        self.media_title.hide(); self.media.hide()

        # 3. Wifi
        self.wifi_row = QHBoxLayout()
        self.wifi = QPushButton("Wifi")
        self.wifi.setCheckable(True)
        self.wifi.clicked.connect(self._set_wifi)
        self.wifi_conn = QLabel("Conexión: ...")
        self.wifi_btn = QPushButton("Redes…")
        self.wifi_btn.clicked.connect(lambda: terminal(['nmtui']))
        self.wifi_row.addWidget(self.wifi)
        self.wifi_row.addWidget(self.wifi_conn)
        self.wifi_row.addWidget(self.wifi_btn)
        self.wifi_conn.setObjectName('hint')
        self.wifi_row.setStretch(1, 1)
        self.section('Wifi')
        self.box.addLayout(self.wifi_row)

        # 4. Bluetooth
        self.bt_row = QHBoxLayout()
        self.bluetooth = QPushButton("Bluetooth")
        self.bluetooth.setCheckable(True)
        self.bluetooth.clicked.connect(self._set_bt)
        self.bt_btn = QPushButton("Dispositivos…")
        self.bt_btn.clicked.connect(lambda: terminal(['bluetoothctl']))
        self.bt_row.addWidget(self.bluetooth)
        self.bt_row.addWidget(self.bt_btn)
        self.bt_row.addStretch(1)
        self.section('Bluetooth')
        self.box.addLayout(self.bt_row)

        # 5. Notificaciones
        self.notif_row = QHBoxLayout()
        self.dnd = QPushButton("No molestar")
        self.dnd.setCheckable(True)
        self.dnd.clicked.connect(self._set_dnd)
        self.btn_last = QPushButton("Ver la última")
        self.btn_last.clicked.connect(lambda: run(['makoctl', 'restore']))
        self.btn_clear = QPushButton("Borrar todas")
        self.btn_clear.clicked.connect(lambda: run(['makoctl', 'dismiss', '-a']))
        self.notif_row.addWidget(self.dnd)
        self.notif_row.addWidget(self.btn_last)
        self.notif_row.addWidget(self.btn_clear)
        self.section('Notificaciones')
        self.box.addLayout(self.notif_row)

        # 6. Fondo animado: opcional, usa la GPU.
        self.living_row = QHBoxLayout()
        self.living = QPushButton('Fondo animado')
        self.living.setCheckable(True)
        self.living.setChecked(getattr(self.shell, 'living_enabled', lambda: False)())
        self.living.setToolTip('La tela del fondo ondula muy despacio. Usa la GPU: mejor apagado en equipos modestos.')
        self.living.toggled.connect(lambda on: getattr(self.shell, 'set_living', lambda _: None)(on))
        self.living_note = QLabel('Usa la GPU', objectName='muted')
        self.living_row.addWidget(self.living); self.living_row.addWidget(self.living_note); self.living_row.addStretch(1)
        self.section('Fondo')
        self.box.addLayout(self.living_row)

        # 7. Sesión: lo que antes solo tenía atajo de teclado, también con el ratón.
        if getattr(shell, 'system_session', False):
            self.section('Sesión')
            self.session_row = QHBoxLayout()
            for text, tip, argv in (('Bloquear', 'Super+L', ['prosperus-bloquear']),
                                    ('Captura', 'Impr Pant · Mayús+Impr Pant: zona · Super+Mayús+S: zona y dibujar', ['prosperus-captura']),
                                    ('Zona', 'Captura de una zona · Mayús+Impr Pant', ['prosperus-captura', 'zona']),
                                    ('Portapapeles', 'Historial del portapapeles · Super+V', ['prosperus-portapapeles']),
                                    ('Escritorio', 'Ocultar o devolver las ventanas del proyecto · Super+D', None)):
                item = QPushButton(text); item.setToolTip(tip)
                item.clicked.connect(lambda checked=False, a=argv: self.session_action(a))
                self.session_row.addWidget(item)
            self.box.addLayout(self.session_row)

        # 8. Footer
        self.foot_row = QHBoxLayout()
        self.btn_ctrl = QPushButton("Controles")
        self.btn_ctrl.clicked.connect(lambda: self.shell.open_controls())
        self.btn_help = QPushButton("Ayuda · F1")
        self.btn_help.clicked.connect(lambda: self.shell.show_help())
        self.box.addSpacing(26)  # sitio para el remate floral
        self.foot_row.addWidget(self.btn_ctrl)
        self.foot_row.addWidget(self.btn_help)
        self.box.addLayout(self.foot_row)

    def session_action(self, argv):
        # Primero se cierra el menú: si no, saldría en la captura o tapando el bloqueo.
        self.shell.quick.menu.close()
        QTimer.singleShot(300, lambda: self.shell.toggle_desktop() if argv is None else QProcess.startDetached(argv[0], argv[1:]))

    def focusNextPrevChild(self, next):
        # Va dentro de un menú: sin esto Tab salta entre las entradas del menú y no entre los controles.
        return cycle_focus(self, next) or super().focusNextPrevChild(next)

    def restyle(self, colors):
        """Colores del proyecto actual: el escritorio lo llama cada vez que cambia el tema o el fondo."""
        c = colors
        self.setStyleSheet(f'''
            #quickSettings {{ background: {c.panel}; border: 1px solid {c.border}; border-radius: 14px; }}
            QLabel {{ color: {c.text}; background: transparent; }}
            QLabel#section {{ color: {c.accent}; font-size: 11px; font-weight: 600; letter-spacing: 1.6px; }}
            QLabel#value, QLabel#hint {{ color: {c.muted}; }}
            QPushButton {{ background: {c.card}; color: {c.text}; border: 1px solid {c.border}; border-radius: 12px;
                           padding: 10px 16px; min-height: 18px; }}
            QPushButton:hover {{ background: {c.hover}; }}
            QPushButton:checked {{ background: {c.hover}; border: 1px solid {c.accent}; }}
            QPushButton:disabled {{ color: {c.border}; }}
            QComboBox {{ background: {c.card}; color: {c.text}; border: 1px solid {c.border}; border-radius: 12px;
                         padding: 8px 14px; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ image: url({arrow('down', c.muted)}); width: 10px; height: 6px; }}
            QComboBox QAbstractItemView {{ background: {c.panel}; color: {c.text}; border: 1px solid {c.border};
                         selection-background-color: {c.hover}; outline: none; padding: 6px; }}
            QPushButton#media {{ font-size: 16px; padding: 6px 14px; }}
            QSlider {{ min-height: 26px; }}
            QSlider::groove:horizontal {{ height: 8px; background: {c.card}; border-radius: 4px; }}
            QSlider::sub-page:horizontal {{ background: {c.accent}; border-radius: 4px; }}
            QSlider::handle:horizontal {{ background: {c.text}; width: 22px; margin: -7px 0; border-radius: 11px; }}''')
        self.update()

    def section(self, text, first=False):
        """Título de sección en versalitas, con aire por encima."""
        if not first:
            self.box.addSpacing(10)
        title = QLabel(text.upper(), objectName='section')
        self.box.addWidget(title)
        return title

    # Remate floral decorativo del panel
    def paintEvent(self, event):
        super().paintEvent(event)
        # Remate floral sobre los botones del pie, como las ramas del mapa.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.shell.colors.text); color.setAlphaF(.3)
        y = self.btn_ctrl.geometry().top() - 22
        flourish(painter, 30, self.width() - 30, y, color, 3)

    # Establece el brillo de la pantalla con el valor seleccionado
    def _set_br(self):
        ok, _ = attempt(['brightnessctl', '-q', '-c', 'backlight', 'set', f'{self.brightness.value()}%'])
        self.br_err.setText('No se pudo cambiar el brillo (detalles en el registro).')
        self.br_err.setVisible(not ok)

    # Ajusta el volumen del sistema
    def _set_vol(self):
        ok, _ = attempt(['wpctl', 'set-volume', '-l', '1.0', '@DEFAULT_AUDIO_SINK@', f'{self.volume.value()/100:.2f}'])
        self.vol_err.setText('No se pudo cambiar el volumen (detalles en el registro).')
        self.vol_err.setVisible(not ok)

    def _set_sink(self, index):
        sink = self.sink.itemData(index)
        if sink is not None:
            run(['wpctl', 'set-default', str(sink)]); self.refresh()

    def _set_mute(self): run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', '1' if self.mute.isChecked() else '0']); self.refresh()
    def _set_wifi(self): run(['nmcli', 'radio', 'wifi', 'on' if self.wifi.isChecked() else 'off']); self.refresh()
    def _set_bt(self): run(['bluetoothctl', 'power', 'on' if self.bluetooth.isChecked() else 'off']); self.refresh()
    def _set_dnd(self): run(['makoctl', 'mode', '-a' if self.dnd.isChecked() else '-r', 'do-not-disturb']); self.refresh()

    def refresh(self):
        # Las órdenes del sistema pueden tardar: se consultan en otro hilo y el panel se abre al instante.
        threading.Thread(target=lambda: self.state_ready.emit(collect()), daemon=True).start()

    # Actualiza el panel rápido con el estado del sistema
    def apply(self, state):
        val_br = state['brightness']
        self.brightness.setEnabled(val_br is not None); self.br_err.setVisible(val_br is None)
        if val_br is not None:
            self.brightness.blockSignals(True); self.brightness.setValue(val_br); self.brightness.blockSignals(False)
            self.br_value.setText(f'{val_br} %')
        else:
            self.br_err.setText('Esta pantalla no permite cambiar el brillo.')
        val_vol = state['volume']
        for widget in (self.volume, self.mute):
            widget.setEnabled(val_vol is not None)
        self.vol_err.setVisible(val_vol is None)
        if val_vol is not None:
            self.volume.blockSignals(True); self.volume.setValue(val_vol[0]); self.volume.blockSignals(False)
            self.vol_value.setText(f'{val_vol[0]} %')
            self.mute.setChecked(val_vol[1])
        else:
            self.vol_err.setText('Sin salida de sonido.')
        sinks = state.get('sinks') or []
        self.sink.blockSignals(True); self.sink.clear()
        for number, name, default in sinks:
            self.sink.addItem('🔊 ' + name, number)
            if default:
                self.sink.setCurrentIndex(self.sink.count() - 1)
        self.sink.blockSignals(False)
        self.sink.setVisible(len(sinks) > 1)
        track = state.get('track')
        self.media.setVisible(track is not None); self.media_title.setVisible(track is not None)
        if track:
            self.play.setText('⏸' if track[0] else '▶'); self.track.setText(track[1])
        is_wifi = state['wifi'] == 'enabled'
        self.wifi.setText('Activado' if is_wifi else 'Desactivado'); self.wifi.setChecked(is_wifi)
        names = [n for n in (state['connections'] or '').splitlines() if n != 'lo']
        self.wifi_conn.setText(', '.join(names) if names else 'Sin conexión')
        bt_st = state['bluetooth']
        self.bluetooth.setEnabled(bt_st is not None); self.bt_btn.setEnabled(bt_st is not None)
        self.bluetooth.setText('No disponible' if bt_st is None else ('Activado' if bt_st else 'Desactivado'))
        self.bluetooth.setChecked(bool(bt_st))
        self.dnd.setChecked('do-not-disturb' in (state['mode'] or ''))


def collect():
    """Estado del sistema; se ejecuta fuera del hilo de la interfaz."""
    # Sin adaptador, bluetoothctl espera a un controlador que no llega: ni se le pregunta.
    adapter = os.path.isdir('/sys/class/bluetooth') and bool(os.listdir('/sys/class/bluetooth'))
    return {'brightness': parse_brightness(run(['brightnessctl', '-m', '-c', 'backlight'])),
            'volume': parse_volume(run(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'])),
            'wifi': run(['nmcli', 'radio', 'wifi']),
            'connections': run(['nmcli', '-t', '-f', 'NAME', 'connection', 'show', '--active']),
            'bluetooth': parse_powered(run(['bluetoothctl', 'show'])) if adapter else None,
            'mode': run(['makoctl', 'mode']),
            'sinks': parse_sinks(run(['wpctl', 'status'])),
            'track': parse_track(quiet(['playerctl', 'metadata', '--format', '{{status}}|{{artist}}|{{title}}']))}


def quiet(argv):
    """Como run, pero sin anotar el fallo: sin reproductor abierto, playerctl falla siempre."""
    try:
        res = subprocess.run(argv, timeout=3, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
