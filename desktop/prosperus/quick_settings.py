# SPDX-License-Identifier: GPL-3.0-only
"""Panel rápido de la esquina derecha: brillo, volumen, wifi, bluetooth y notificaciones."""
import subprocess
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QPushButton, QWidget)
from PySide6.QtCore import QProcess, Qt

def run(argv):
    """Ejecuta un comando sin shell y captura la salida."""
    try:
        res = subprocess.run(argv, timeout=3, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except (subprocess.SubprocessError, OSError, subprocess.TimeoutExpired):
        return None

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

def parse_powered(text):
    """Parsea salida de bluetoothctl show."""
    if not text: return None
    for line in text.splitlines():
        if line.strip().startswith("Powered:"):
            return line.split(":", 1)[1].strip() == "yes"
    return None

def terminal(argv):
    """Abre una herramienta de texto (nmtui, bluetoothctl) en la consola."""
    QProcess.startDetached('foot', argv)


class QuickSettings(QFrame):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.setObjectName("quickSettings")
        self.box = QVBoxLayout(self)
        
        # 1. Brillo
        self.br_row = QHBoxLayout()
        self.br_lbl = QLabel("Brillo:")
        self.brightness = QSlider(Qt.Horizontal)
        self.brightness.setRange(5, 100)
        self.brightness.sliderReleased.connect(self._set_br)
        self.br_err = QLabel("Esta pantalla no permite cambiar el brillo.")
        self.br_err.hide()
        self.br_row.addWidget(self.br_lbl)
        self.br_row.addWidget(self.brightness)
        self.box.addLayout(self.br_row)
        self.box.addWidget(self.br_err)

        # 2. Volumen
        self.vol_row = QHBoxLayout()
        self.vol_lbl = QLabel("Volumen:")
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.sliderReleased.connect(self._set_vol)
        self.mute = QPushButton("Silencio")
        self.mute.setCheckable(True)
        self.mute.clicked.connect(self._set_mute)
        self.vol_err = QLabel("Sin salida de sonido.")
        self.vol_err.hide()
        self.vol_row.addWidget(self.vol_lbl)
        self.vol_row.addWidget(self.volume)
        self.vol_row.addWidget(self.mute)
        self.box.addLayout(self.vol_row)
        self.box.addWidget(self.vol_err)

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
        self.box.addWidget(QLabel('Wifi'))
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
        self.box.addWidget(QLabel('Bluetooth'))
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
        self.box.addWidget(QLabel('Notificaciones'))
        self.box.addLayout(self.notif_row)

        # 6. Footer
        self.foot_row = QHBoxLayout()
        self.btn_ctrl = QPushButton("Controles")
        self.btn_ctrl.clicked.connect(lambda: self.shell.open_controls())
        self.btn_help = QPushButton("Ayuda · F1")
        self.btn_help.clicked.connect(lambda: self.shell.show_help())
        self.foot_row.addWidget(self.btn_ctrl)
        self.foot_row.addWidget(self.btn_help)
        self.box.addLayout(self.foot_row)

    def _set_br(self): run(['brightnessctl', 'set', f'{self.brightness.value()}%'])
    def _set_vol(self): run(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', f'{self.volume.value()/100:.2f}'])
    def _set_mute(self): run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', '1' if self.mute.isChecked() else '0']); self.refresh()
    def _set_wifi(self): run(['nmcli', 'radio', 'wifi', 'on' if self.wifi.isChecked() else 'off']); self.refresh()
    def _set_bt(self): run(['bluetoothctl', 'power', 'on' if self.bluetooth.isChecked() else 'off']); self.refresh()
    def _set_dnd(self): run(['makoctl', 'mode', '-a' if self.dnd.isChecked() else '-r', 'do-not-disturb']); self.refresh()

    def refresh(self):
        # Brillo
        val_br = parse_brightness(run(['brightnessctl', '-m']))
        if val_br is not None:
            self.brightness.setValue(val_br)
            self.brightness.setEnabled(True)
            self.br_err.hide()
        else:
            self.brightness.setEnabled(False)
            self.br_err.show()
        # Volumen
        val_vol = parse_volume(run(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@']))
        if val_vol is not None:
            self.volume.setValue(val_vol[0])
            self.mute.setChecked(val_vol[1])
            self.volume.setEnabled(True)
            self.mute.setEnabled(True)
            self.vol_err.hide()
        else:
            self.volume.setEnabled(False)
            self.mute.setEnabled(False)
            self.vol_err.show()
        # Wifi
        wifi_st = run(['nmcli', 'radio', 'wifi'])
        is_wifi = wifi_st == 'enabled'
        self.wifi.setText('Activado' if is_wifi else 'Desactivado')
        self.wifi.setChecked(is_wifi)
        conns = run(['nmcli', '-t', '-f', 'NAME', 'connection', 'show', '--active'])
        if conns:
            names = [n for n in conns.splitlines() if n != 'lo']
            self.wifi_conn.setText(", ".join(names) if names else "Sin conexión")
        else: self.wifi_conn.setText("Sin conexión")
        # Bluetooth
        bt_st = parse_powered(run(['bluetoothctl', 'show']))
        if bt_st is not None:
            self.bluetooth.setText("Bluetooth" if bt_st else "Bluetooth (Off)")
            self.bluetooth.setChecked(bt_st)
            self.bluetooth.setEnabled(True)
        else:
            self.bluetooth.setText("No disponible")
            self.bluetooth.setEnabled(False)
        # Notificaciones
        mako = run(['makoctl', 'mode']) or ""
        self.dnd.setChecked('do-not-disturb' in mako)
