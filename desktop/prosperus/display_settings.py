"""Monitores en Sway: extender, duplicar o usar solo la pantalla principal."""
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import json
import subprocess
from pathlib import Path

CONFIG = Path.home() / '.config/prosperus/displays.json'
DEFAULTS = {'mode': 'extend', 'primary': '', 'position': 'right'}
MODES = [('extend', 'Extender escritorio'), ('mirror', 'Duplicar pantalla principal'),
         ('single', 'Solo la pantalla principal')]
POSITIONS = [('right', 'Derecha'), ('left', 'Izquierda'), ('above', 'Encima'), ('below', 'Debajo')]


def parse_outputs(text):
    """Salidas de `swaymsg -t get_outputs -r` con su tamaño lógico."""
    outputs = []
    for item in json.loads(text):
        if not item.get('name'):
            continue
        mode = item.get('current_mode') or (item.get('modes') or [{}])[0]
        scale = float(item.get('scale') or 1.0)
        outputs.append({
            'name': item['name'],
            'description': f"{item.get('make', '')} {item.get('model', '')}".strip() or item['name'],
            'active': bool(item.get('active')),
            'width': int(mode.get('width', 0)), 'height': int(mode.get('height', 0)),
            'scale': scale if scale > 0 else 1.0,
        })
    return outputs


def _primary(outputs, primary):
    names = [o['name'] for o in outputs]
    return primary if primary in names else names[0]


def plan_commands(outputs, mode, primary, position):
    """Órdenes de Sway: la principal en 0,0 y las demás encadenadas en el lado elegido."""
    if not outputs:
        return []
    primary = _primary(outputs, primary)
    main = next(o for o in outputs if o['name'] == primary)
    commands = [f'output "{primary}" enable pos 0 0']
    # Desplazamiento acumulado en píxeles lógicos (el escalado reduce el tamaño).
    x = round(main['width'] / main['scale']) if position == 'right' else 0
    y = round(main['height'] / main['scale']) if position == 'below' else 0
    for o in outputs:
        if o['name'] == primary:
            continue
        if mode == 'single':
            commands.append(f'output "{o["name"]}" disable')
            continue
        w, h = round(o['width'] / o['scale']), round(o['height'] / o['scale'])
        if position == 'left':
            x -= w
        elif position == 'above':
            y -= h
        commands.append(f'output "{o["name"]}" enable pos {x} {y}')
        if position == 'right':
            x += w
        elif position == 'below':
            y += h
    return commands


def mirror_commands(outputs, primary):
    """wl-mirror muestra la principal a pantalla completa en cada salida secundaria."""
    if not outputs:
        return []
    primary = _primary(outputs, primary)
    return [['wl-mirror', '--fullscreen-output', o['name'], primary]
            for o in outputs if o['name'] != primary]


def load_config(path=None):
    config = dict(DEFAULTS)
    try:
        data = json.loads(Path(path or CONFIG).read_text(encoding='utf-8'))
        if isinstance(data, dict):
            config.update({k: v for k, v in data.items() if k in DEFAULTS and isinstance(v, str)})
    except (OSError, ValueError):
        pass
    return config


def save_config(config, path=None):
    path = Path(path or CONFIG)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def read_outputs():
    try:
        result = subprocess.run(['swaymsg', '-t', 'get_outputs', '-r'], capture_output=True,
                                text=True, timeout=5, check=True)
        return parse_outputs(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return []


def apply(config):
    outputs = read_outputs()
    if not outputs:
        return 'No se detectan monitores (¿sesión Sway?).'
    try:
        subprocess.run(['pkill', '-x', 'wl-mirror'], capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass
    commands = plan_commands(outputs, config['mode'], config['primary'], config['position'])
    try:
        result = subprocess.run(['swaymsg', '; '.join(commands)], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as error:
        return str(error)
    if result.returncode:
        return result.stderr.strip() or 'Sway rechazó la configuración.'
    if config['mode'] == 'mirror':
        try:
            for argv in mirror_commands(outputs, config['primary']):
                subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        except FileNotFoundError:
            return 'Falta wl-mirror para duplicar pantallas.'
    return 'Pantallas aplicadas.'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Aplica la configuración de monitores guardada.')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    if args.apply:
        print(apply(load_config()))
    return 0


try:
    from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
                                   QPushButton, QVBoxLayout)
except ImportError:  # el CLI de arranque no necesita Qt
    QDialog = object


class DisplayDialog(QDialog):
    """Elegir modo, pantalla principal y lado donde van las demás."""

    def __init__(self, parent=None, outputs=None):
        super().__init__(parent)
        self.setWindowTitle('Monitores'); self.resize(480, 260)
        self._outputs_provider = (lambda: outputs) if outputs is not None else read_outputs
        layout = QVBoxLayout(self)
        self.detected = QLabel(); self.detected.setWordWrap(True); layout.addWidget(self.detected)
        form = QFormLayout(); layout.addLayout(form)
        self.mode_choice = QComboBox(); self.primary_choice = QComboBox(); self.position_choice = QComboBox()
        for combo, items in [(self.mode_choice, MODES), (self.position_choice, POSITIONS)]:
            for data, label in items:
                combo.addItem(label, data)
        form.addRow('Modo', self.mode_choice)
        form.addRow('Principal', self.primary_choice)
        form.addRow('Las demás, a la', self.position_choice)
        self.status = QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        for text, slot in [('Detectar de nuevo', self.reload), ('Aplicar', self.apply), ('Cerrar', self.reject)]:
            button = QPushButton(text); button.clicked.connect(slot); buttons.addWidget(button)
        self.mode_choice.currentIndexChanged.connect(self._update_position)
        config = load_config()
        self.mode_choice.setCurrentIndex(max(0, self.mode_choice.findData(config['mode'])))
        self.position_choice.setCurrentIndex(max(0, self.position_choice.findData(config['position'])))
        self.reload(primary=config['primary'])

    def reload(self, *_, primary=None):
        primary = primary if primary is not None else self.primary_choice.currentData()
        self.outputs = self._outputs_provider()
        self.detected.setText('\n'.join(f"{o['name']} · {o['description']} · {o['width']}x{o['height']}"
                                        for o in self.outputs) or 'No se detectan monitores.')
        self.primary_choice.clear()
        for o in self.outputs:
            self.primary_choice.addItem(f"{o['name']} · {o['description']}", o['name'])
        self.primary_choice.setCurrentIndex(max(0, self.primary_choice.findData(primary)))
        self.status.setText('' if len(self.outputs) > 1 else
                            'Solo hay un monitor conectado. Conecta otro y pulsa «Detectar de nuevo».')
        self._update_position()

    def _update_position(self, *_):
        self.position_choice.setEnabled(self.mode_choice.currentData() == 'extend')

    def current_config(self):
        return {'mode': self.mode_choice.currentData(), 'primary': self.primary_choice.currentData() or '',
                'position': self.position_choice.currentData()}

    def apply(self):
        config = self.current_config()
        save_config(config)
        self.status.setText(apply(config))


if __name__ == '__main__':
    raise SystemExit(main())
