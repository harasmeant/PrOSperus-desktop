"""Asistente de controladores: detecta la gráfica y recomienda qué instalar.

La detección es de solo lectura (sysfs). La instalación nunca es silenciosa:
se abre una terminal con las órdenes visibles y sudo puede pedir contraseña.
"""
# SPDX-License-Identifier: GPL-3.0-only
from dataclasses import dataclass, field
from pathlib import Path
import shlex
import subprocess

from PySide6.QtWidgets import (QButtonGroup, QDialog, QHBoxLayout, QLabel, QPushButton,
                               QRadioButton, QVBoxLayout)

NVIDIA, INTEL, AMD = '0x10de', '0x8086', '0x1002'
VIRTUAL = {'0x1af4': 'Virtio', '0x1234': 'QEMU', '0x15ad': 'VMware', '0x80ee': 'VirtualBox', '0x1b36': 'Red Hat QXL'}
# Primer identificador de Turing (TU102 = 0x1e02). Desde Turing, NVIDIA usa
# módulos de núcleo abiertos y NVK (Mesa) ofrece Vulkan con el driver libre.
TURING_FIRST = 0x1e00
SECURE_BOOT = Path('/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c')

RPMFUSION = ('sudo dnf install -y '
             'https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm '
             'https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm')
OPEN_STACK = 'sudo dnf install -y kernel-modules linux-firmware mesa-vulkan-drivers'


@dataclass(frozen=True)
class Gpu:
    vendor: str
    device: int
    driver: str
    slot: str

    # Identifica la tarjeta gráfica para recomendar controladores
    @property
    def name(self):
        names = {NVIDIA: 'NVIDIA', INTEL: 'Intel', AMD: 'AMD', **VIRTUAL}
        return f'{names.get(self.vendor, self.vendor)} {self.device:#06x}'


@dataclass(frozen=True)
class Option:
    key: str
    title: str
    detail: str
    commands: tuple = ()
    recommended: bool = False


@dataclass
class Plan:
    gpu: Gpu
    summary: str
    options: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def detect_gpus(root=Path('/sys/bus/pci/devices')):
    """Tarjetas gráficas PCI (clase 0x03) del sistema que ejecuta este proceso."""
    gpus = []
    for path in sorted(root.iterdir()):
        try:
            if int((path / 'class').read_text().strip(), 16) >> 16 != 0x03:
                continue
            driver = (path / 'driver').resolve(strict=True).name if (path / 'driver').is_symlink() else ''
            gpus.append(Gpu((path / 'vendor').read_text().strip().lower(),
                            int((path / 'device').read_text().strip(), 16), driver, path.name))
        except (OSError, ValueError):
            continue
    return gpus


# Indica si Secure Boot está habilitado
def secure_boot_enabled(path=SECURE_BOOT):
    try:
        return path.read_bytes()[-1] == 1  # 4 bytes de atributos + 1 byte de valor
    except (OSError, IndexError):
        return False


# Recomienda controladores según la gráfica detectada
def plan_for(gpu, secure_boot=False):
    if gpu.vendor in VIRTUAL:
        return Plan(gpu, 'Gráfica virtual: el sistema ya incluye lo necesario.')
    if gpu.vendor in (INTEL, AMD):
        return Plan(gpu, 'Intel y AMD funcionan con controladores libres (Mesa).', [
            Option('open', 'Controladores libres completos',
                   'Módulos del núcleo, firmware y Vulkan para juegos, Blender y FreeCAD.',
                   (OPEN_STACK,), recommended=True),
            Option('none', 'No instalar nada ahora', 'Puedes volver desde Controles › Hardware y drivers.')])
    if gpu.vendor != NVIDIA:
        return Plan(gpu, 'Fabricante no reconocido: no hay recomendación automática.')
    if gpu.device >= TURING_FIRST:
        warnings = ['El controlador propietario se compila en este equipo (akmods) y requiere reiniciar.']
        if secure_boot:
            warnings.append('Secure Boot está activo: habrá que registrar la clave del módulo (MOK) '
                            'o el controlador propietario no cargará. Las órdenes la preparan; '
                            'al reiniciar, acepta la clave con la contraseña que elijas.')
        proprietary = [RPMFUSION, 'sudo dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda "kernel-devel-$(uname -r)"',
                       'sudo akmods --force']
        if secure_boot:
            proprietary[2:2] = ['sudo dnf install -y mokutil', 'sudo kmodgenca -a',
                                'sudo mokutil --import /etc/pki/akmods/certs/public_key.der']
        return Plan(gpu, 'NVIDIA Turing o posterior (RTX, GTX 16xx o más nueva).', [
            Option('proprietary', 'Propietario NVIDIA (RPM Fusion)',
                   'Máximo rendimiento y CUDA/OptiX para Blender Cycles y cálculo. Recomendado para ingeniería.',
                   tuple(proprietary), recommended=True),
            Option('open', 'Libre: nouveau + NVK',
                   'Sin compilar nada y compatible con Secure Boot. Vulkan con NVK; sin CUDA.',
                   (OPEN_STACK,)),
            Option('none', 'No instalar nada ahora', 'Puedes volver desde Controles › Hardware y drivers.')],
            warnings)
    return Plan(gpu, 'NVIDIA anterior a Turing: el controlador propietario actual ya no la admite.', [
        Option('open', 'Libre: nouveau', 'Escritorio y aplicaciones básicas; rendimiento 3D limitado.',
               (OPEN_STACK,), recommended=True),
        Option('none', 'No instalar nada ahora',
               'Las series heredadas del controlador propietario se consultan en RPM Fusion.')])


def needs_attention(plans):
    return any(plan.options for plan in plans)


def terminal_command(commands):
    """Orden para foot: muestra cada paso, se detiene en el primer fallo y espera."""
    script = ' && '.join(f'echo {shlex.quote("$ " + c)} && {c}' for c in commands)
    script = (f'({script}) && echo && echo "Listo. Reinicia para cargar el controlador." '
              f'|| echo "La instalación se detuvo por un error."; read -r -p "Pulsa Intro para cerrar" _')
    return ['prosperus-terminal', '--title', 'PrOSperus · Instalar controladores', 'sh', '-c', script]


class DriverAssistant(QDialog):
    # Recomienda drivers gráficos para la tarjeta detectada
    def __init__(self, shell, plans=None):
        super().__init__(shell)
        self.shell = shell
        self.setWindowTitle('Controladores de gráfica'); self.resize(640, 420)
        # El estilo general oculta el círculo de las opciones no marcadas.
        self.setStyleSheet('QRadioButton::indicator { width: 14px; height: 14px; border-radius: 8px;'
                           ' border: 1px solid palette(mid); }'
                           ' QRadioButton::indicator:checked { background: palette(highlight); }')
        self.plans = plans if plans is not None else [plan_for(g, secure_boot_enabled()) for g in detect_gpus()]
        layout = QVBoxLayout(self)
        self.groups = []
        if not self.plans:
            layout.addWidget(QLabel('No se detectó ninguna tarjeta gráfica PCI.'))
        for plan in self.plans:
            title = QLabel(f'<b>{plan.gpu.name}</b> · driver actual: {plan.gpu.driver or "ninguno"}')
            layout.addWidget(title)
            summary = QLabel(plan.summary); summary.setWordWrap(True); layout.addWidget(summary)
            for warning in plan.warnings:
                note = QLabel('⚠ ' + warning); note.setWordWrap(True); layout.addWidget(note)
            group = QButtonGroup(self)
            for option in plan.options:
                radio = QRadioButton(option.title + (' (recomendado)' if option.recommended else ''))
                radio.setToolTip(option.detail); radio.setChecked(option.recommended)
                group.addButton(radio); layout.addWidget(radio)
                detail = QLabel(option.detail); detail.setWordWrap(True); detail.setIndent(24); layout.addWidget(detail)
                radio.option = option
            self.groups.append(group)
        self.status = QLabel(''); self.status.setWordWrap(True); layout.addWidget(self.status)
        layout.addStretch()
        row = QHBoxLayout(); row.addStretch()
        later = QPushButton('Más tarde'); later.clicked.connect(self.reject); row.addWidget(later)
        self.install = QPushButton('Instalar selección'); self.install.clicked.connect(self.run)
        self.install.setEnabled(needs_attention(self.plans)); row.addWidget(self.install)
        layout.addLayout(row)

    # Obtiene comandos únicos para instalar controladores
    def selected_commands(self):
        commands = []
        for group in self.groups:
            button = group.checkedButton()
            if button is not None:
                commands += [c for c in button.option.commands if c not in commands]
        return commands

    # Ejecuta comandos de instalación en terminal visible con sudo
    def run(self):
        commands = self.selected_commands()
        if not commands:
            self.accept(); return
        try:
            subprocess.Popen(terminal_command(commands), start_new_session=True)
            self.accept()
        except OSError as error:
            self.status.setText('No se pudo abrir la terminal de instalación: ' + str(error))
