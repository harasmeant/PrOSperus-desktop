"""Read-only PCI inventory: a bound driver is not a hardware validation."""
# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path

from PySide6.QtWidgets import (QApplication, QDialog, QHeaderView, QLabel,
                              QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

# IDs de proveedor PCI y sus nombres comerciales
VENDORS = {'0x8086': 'Intel', '0x1002': 'AMD', '0x1022': 'AMD',
           '0x10de': 'NVIDIA', '0x10ec': 'Realtek', '0x1af4': 'Virtio'}
# Clases de dispositivo que interesa mostrar (gráfica, red, audio)
CLASSES = {0x03: 'Gráfica', 0x02: 'Red', 0x04: 'Audio / multimedia'}


# Lee sysfs y devuelve dispositivos PCI con clase de interés
def pci_devices(root=Path('/sys/bus/pci/devices')):
    devices = []
    # Sysfs describes the system running this process (the guest in a VM).
    for path in sorted(root.iterdir()):
        try:
            # El registro de clase guarda el código en los bits altos
            kind = CLASSES.get(int((path / 'class').read_text().strip(), 16) >> 16)
            if kind is None:
                continue
            vendor = (path / 'vendor').read_text().strip()
            identity = (path / 'device').read_text().strip()
            # driver es un symlink; extraemos solo el nombre del controlador
            driver = (path / 'driver').resolve(strict=True).name if (path / 'driver').is_symlink() else ''
            devices.append((f'{kind} · {VENDORS.get(vendor, vendor)} {identity}', driver,
                            'Controlador asociado' if driver else 'Sin controlador asociado', path.name))
        except (OSError, ValueError):
            # Fila de fallback cuando no se puede leer un dispositivo
            devices.append((path.name, '', 'No se pudo leer; pulsa Actualizar', path.name))
    return devices


# Diálogo de solo lectura que lista dispositivos PCI y su controlador
class HardwareDialog(QDialog):
    def __init__(self, shell):
        # Configura la ventana: tabla, avisos y botones
        super().__init__(shell)
        self.setWindowTitle('Hardware y drivers'); self.resize(780, 480)
        layout = QVBoxLayout(self)
        info = QLabel('Gráficos, red y audio PCI del sistema actual. En una máquina virtual '
                      'verás sus dispositivos virtuales. Un controlador asociado no confirma '
                      'que el dispositivo funcione correctamente.')
        info.setWordWrap(True); layout.addWidget(info)
        self.devices = QTreeWidget(); self.devices.setHeaderLabels(['Dispositivo', 'Driver', 'Estado'])
        self.devices.setAccessibleName('Dispositivos PCI y controladores asociados')
        # Nombre accesible para lectores de pantalla
        self.devices.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # Qt ajusta el ancho de columnas al contenido
        layout.addWidget(self.devices)
        self.status = QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        scope = QLabel('El asistente recomienda e instala controladores de gráfica. '
                       'USB, impresoras, Bluetooth y firmware requieren comprobaciones adicionales.')
        scope.setWordWrap(True); layout.addWidget(scope)
        # Guardamos el shell para abrir el asistente desde aquí
        self.shell = shell
        for title, action in [('Asistente de controladores…', self.open_assistant), ('Actualizar', self.refresh), ('Copiar diagnóstico', self.copy), ('Cerrar', self.accept)]:
            button = QPushButton(title); button.clicked.connect(action); layout.addWidget(button)
        # Carga inicial de dispositivos al abrir
        self.refresh()

    def refresh(self):
        # Rellena el árbol y actualiza la etiqueta de estado
        self.devices.clear()
        try:
            self.rows = pci_devices()
            for name, driver, state, address in self.rows:
                # Guion cuando no hay driver asociado
                item = QTreeWidgetItem([name, driver or '—', state])
                item.setToolTip(0, 'Dirección PCI: ' + address)
                # Dirección PCI completa como información adicional
                self.devices.addTopLevelItem(item)
            self.status.setText(f'{len(self.rows)} dispositivos PCI detectados.' if self.rows
                                else 'No se encontraron dispositivos PCI de gráficos, red o audio.')
        except OSError as error:
            # sysfs puede no estar accesible o faltar permiso
            self.rows = []
            self.status.setText('No se pudo consultar el hardware: ' + str(error))

    def open_assistant(self):
        # Importación diferida para evitar ciclos; abre el asistente
        from .driver_assistant import DriverAssistant
        from .shell import show_dialog
        show_dialog(DriverAssistant(self.shell))

    def copy(self):
        # Copia el diagnóstico al portapapeles (no valida funcionamiento)
        QApplication.clipboard().setText('PrOSperus · diagnóstico PCI (no valida funcionamiento)\n' +
            self.status.text() + '\n' + '\n'.join(' | '.join(row) for row in self.rows))
