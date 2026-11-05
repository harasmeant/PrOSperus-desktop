# SPDX-License-Identifier: GPL-3.0-only
"""Instalar programas del sistema (pacman en Arch, dnf5 en Fedora) y de Flathub, o un paquete local."""
from pathlib import Path
import re
import subprocess
import sys

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt
from PySide6.QtGui import QColor, QFont
from .window_header import WindowHeader
from .theme_state import current_palette
from . import distro
from .recommended import is_installed, package_ids, recommended
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

# Expresión regular que define los caracteres permitidos en el término de búsqueda para evitar inyección en shell.
ASKPASS = '/usr/bin/prosperus-askpass'
SAFE = re.compile(r'^[\w .+-]+$')


# Busca programas en el sistema (pacman o dnf) y en Flathub
def search_commands(text, system=None):
    # Retorna una lista de tuplas (source, argv) para cada fuente válida.
    system = system or distro.current()
    term = text.strip()
    # Nunca pasa por un shell, pero una búsqueda rara no es un nombre de programa.
    if not term or not SAFE.match(term):
        return []
    return [('system', system.search_command(term)),
            ('flathub', ['flatpak', 'search', '--columns=application,name,description', term])]


# Filtra aplicaciones Flathub por ID con punto
def parse_flatpak(output):
    # Analiza la salida tabulado de `flatpak search` de Flathub.
    # El ID del flatpak (columna 0) debe contener un punto para filtrar aplicaciones internas o de prueba.
    found = []
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) >= 2 and '.' in parts[0]:
            found.append({'source': 'flathub', 'id': parts[0].strip(), 'name': parts[1].strip(),
                          'summary': parts[2].strip() if len(parts) > 2 else ''})
    return found


# Genera comandos de instalación para el sistema, Flathub o un paquete local
def install_command(item, system=None):
    system = system or distro.current()
    if item['source'] == 'system':
        return system.install_command(package_ids(item, system).split())
    if item['source'] == 'flathub':
        return ['sudo', '-A', 'flatpak', 'install', '-y', '--noninteractive', 'flathub', item['id']]
    path = str(item['id'])
    if path.lower().endswith(system.package_suffixes):
        return system.install_file_command(path)
    if path.lower().endswith('.flatpakref'):
        return ['sudo', '-A', 'flatpak', 'install', '-y', '--noninteractive', '--from', path]
    raise ValueError(f"Solo se instalan archivos {' o '.join(system.package_suffixes)} o .flatpakref.")


# Debian llama al servicio por su nombre real; el alias de siempre no se puede activar.
DEBIAN_SERVICES = {'input-remapper': 'input-remapper-daemon'}


def after_commands(item, system=None):
    """Servicios que activar tras instalar (p. ej. el demonio de Input Remapper)."""
    system = system or distro.current()
    rename = DEBIAN_SERVICES if system.key == 'debian' else {}
    return [['sudo', '-A', 'systemctl', 'enable', '--now', rename.get(name, name)] for name in item.get('after', ())]


def installed_names():
    """(aplicaciones de Flathub, paquetes del sistema) ya instalados; vacío si no se puede saber."""
    def names(argv):
        try:
            return set(subprocess.run(argv, capture_output=True, text=True, timeout=10).stdout.split())
        except (OSError, subprocess.SubprocessError):
            return set()
    return (names(['flatpak', 'list', '--app', '--columns=application']),
            names(distro.current().installed_command()))


# Define estilos visuales de la interfaz
def style(c):
    # Tono del proyecto que se ve en el escritorio (theme_state), no siempre verde.
    return c.css() + f'''
Installer {{ background: {c.base}; }}
QLabel#title {{ font-size: 20px; font-weight: bold; }}
QLineEdit {{ font-size: 15px; }}
QListWidget::item:selected {{ border: 2px solid {c.accent}; background: {c.card}; }}
QPlainTextEdit {{ background: {c.panel}; border: 1px solid {c.border}; border-radius: 10px; padding: 8px 10px; font-size: 12px; }}
'''


def persistence_note(marker='/run/prosperus-persistent', system_marker='/run/prosperus-system-persistent'):
    """Qué se conserva al apagar según haya persistencia en el USB (carpeta personal y, aparte, el sistema)."""
    if Path(marker).exists() and Path(system_marker).exists():
        return f'USB persistente: lo que instales, de {distro.current().label} o de Flathub, se conserva al apagar.'
    if Path(marker).exists():
        return ('Con el USB persistente, los programas de Flathub se conservan al apagar; '
                f'los de {distro.current().label} se pierden.')
    return 'Sesión sin persistencia: lo que instales se perderá al apagar.'


class Installer(QWidget):
    # Interfaz gráfica principal que coordina búsquedas, instalación y registro de actividad.
    def __init__(self, path=None):
        super().__init__()
        self.setWindowTitle('Instalar programas'); self.resize(760, 560); self.setStyleSheet(style(current_palette()))
        self.searches, self.results, self.job, self.pending = [], {}, None, []
        self.showing_recommended = False
        self.colors = current_palette()
        layout = QVBoxLayout(self)
        layout.addWidget(WindowHeader('Instalar programas', self))
        self.search = QLineEdit(); self.search.setPlaceholderText('Busca un programa, o mira las recomendadas abajo')
        self.search.returnPressed.connect(self.run_search); layout.addWidget(self.search)
        self.list = QListWidget(); self.list.itemActivated.connect(lambda _: self.install()); layout.addWidget(self.list)
        note = QLabel(persistence_note()); note.setObjectName('muted'); note.setWordWrap(True); layout.addWidget(note)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(120); layout.addWidget(self.log)
        row = QHBoxLayout()
        suggested = QPushButton('Recomendadas'); suggested.clicked.connect(self.show_recommended); row.addWidget(suggested)
        row.addStretch()
        self.install_button = QPushButton('Instalar'); self.install_button.clicked.connect(lambda: self.install())
        close = QPushButton('Cerrar'); close.clicked.connect(self.close)
        row.addWidget(self.install_button); row.addWidget(close); layout.addLayout(row)
        if path:
            self.show_items([{'source': 'file', 'id': str(Path(path).resolve()), 'name': Path(path).name, 'summary': 'Archivo local'}])
        else:
            self.show_recommended()
        self.search.setFocus()

    # Mostrar ítems con origen y resumen
    def show_items(self, items):
        self.showing_recommended = False
        # Limpia la lista y muestra los ítems; asigna prefijos visuales (`[Arch]`, `[Flathub]`, `[Archivo]`) según el origen.
        self.list.clear()
        for item in items:
            tag = {'system': f'[{distro.current().label}]', 'flathub': '[Flathub]'}.get(item['source'], '[Archivo]')
            widget = QListWidgetItem(f"{tag}  {item['name']} — {item['summary']}")
            widget.setData(Qt.ItemDataRole.UserRole, item); self.list.addItem(widget)
        if self.list.count():
            self.list.setCurrentRow(0)

    # Muestra programas recomendados con estado de instalación
    def show_recommended(self):
        # Catálogo por categorías; las que ya están instaladas llevan ✓.
        flatpaks, packages = installed_names()
        self.list.clear(); category = None; self.showing_recommended = True
        for entry in recommended():
            if entry['category'] != category:
                category = entry['category']
                header = QListWidgetItem(category.upper()); header.setFlags(Qt.ItemFlag.NoItemFlags)
                font = QFont(); font.setPointSizeF(8.5); font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
                header.setFont(font); header.setForeground(QColor(self.colors.accent)); self.list.addItem(header)
            done = is_installed(entry, flatpaks, packages)
            origin = distro.current().label if entry['source'] == 'system' else 'Flathub'
            widget = QListWidgetItem(f"{'✓  ' if done else '     '}{entry['name']} — {entry['summary']}   · {origin}")
            widget.setData(Qt.ItemDataRole.UserRole, dict(entry, installed=done))
            if done:
                widget.setForeground(QColor(self.colors.muted))
            self.list.addItem(widget)
        self.list.setCurrentRow(1)
        self.log.setPlainText('Elige un programa y pulsa Instalar (o doble clic). ✓ = ya instalado.')

    # Buscar programas en el sistema y en Flathub
    def run_search(self):
        # Obtiene los comandos válidos y ejecuta ambos procesos en paralelo (sistema y Flathub).
        if not self.search.text().strip():
            self.show_recommended(); return
        commands = search_commands(self.search.text())
        if not commands:
            self.log.setPlainText('Escribe un nombre de programa (letras, números, - _ . +).'); return
        self.results = {}; self.list.clear(); self.log.setPlainText('Buscando…')
        for source, argv in commands:
            process = QProcess(self); self.searches.append(process)
            process.finished.connect(lambda code, status, p=process, s=source: self.search_done(p, s))
            process.errorOccurred.connect(lambda error, p=process: self.failed(p, error))
            process.start(argv[0], argv[1:])

    # Avisa si un comando de búsqueda no llega a arrancar
    def failed(self, process, error):
        # Muestra un error si el comando externo no puede iniciarse (ej. ejecutable no encontrado).
        if error == QProcess.ProcessError.FailedToStart:
            self.log.appendPlainText('No está disponible: ' + process.program())
            self.search_done(process, None)

    # Mostrar programas encontrados en el sistema y en Flathub
    def search_done(self, process, source):
        # Procesa la salida finalizada de un proceso de búsqueda, la guarda y actualiza la lista de la interfaz.
        if process not in self.searches:
            return
        self.searches.remove(process)
        if source:
            output = bytes(process.readAllStandardOutput()).decode(errors='replace')
            self.results[source] = (distro.current().parse_search if source == 'system' else parse_flatpak)(output)
            if process.exitCode() and not self.results[source]:
                self.log.appendPlainText(bytes(process.readAllStandardError()).decode(errors='replace').strip())
        process.deleteLater()
        items = self.results.get('system', []) + self.results.get('flathub', [])
        self.show_items(items)
        if not self.searches:
            self.log.appendPlainText(f'{len(items)} resultados.')

    # Inicia instalación de programas desde repositorios o archivos locales
    def install(self):
        # Inicia el proceso de instalación para el ítem seleccionado si no hay otra instalación en curso.
        current = self.list.currentItem()
        if current is None or self.job is not None:
            return
        item = current.data(Qt.ItemDataRole.UserRole)
        if item is None:
            return
        if item.get('installed'):
            self.log.setPlainText(item['name'] + ' ya está instalado: búscalo en Aplicaciones.'); return
        try:
            argv = install_command(item)
        except ValueError as error:
            QMessageBox.warning(self, 'Instalar', str(error)); return
        if item['source'] == 'file' and QMessageBox.question(self, 'Instalar', f"¿Instalar {item['name']}?") != QMessageBox.StandardButton.Yes:
            return
        self.log.setPlainText('Instalando ' + item['name'] + '…')
        self.pending = after_commands(item)
        self.run_job(argv)

    # Lanza un paso (instalar o activar un servicio) y vuelca su salida al registro
    def run_job(self, argv):
        self.job = QProcess(self); self.job.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.job.readyReadStandardOutput.connect(lambda: self.log.appendPlainText(bytes(self.job.readAllStandardOutput()).decode(errors='replace').rstrip()))
        self.job.finished.connect(self.install_done)
        # sudo -A pide la contraseña con una ventana (en la Live no la pide: NOPASSWD).
        env = QProcessEnvironment.systemEnvironment()
        if not env.contains('SUDO_ASKPASS'):
            env.insert('SUDO_ASKPASS', ASKPASS)
        self.job.setProcessEnvironment(env)
        self.install_button.setEnabled(False)
        self.job.start(argv[0], argv[1:])

    # Procesa resultados de instalación y actualiza interfaz
    def install_done(self, code, status):
        # Actualiza el registro de actividad, libera el estado del trabajo y cierra la aplicación si la ventana está oculta.
        ok = code == 0 and status == QProcess.ExitStatus.NormalExit
        self.job.deleteLater(); self.job = None
        if ok and self.pending:
            argv = self.pending.pop(0); self.log.appendPlainText('Activando ' + argv[-1] + '…')
            self.run_job(argv); return
        self.pending = []
        self.log.appendPlainText('Instalado.' if ok else f'Error (código {code}).')
        self.install_button.setEnabled(True)
        if ok and self.showing_recommended:
            row = self.list.currentRow(); log = self.log.toPlainText()
            self.show_recommended(); self.list.setCurrentRow(row); self.log.setPlainText(log)
        if not self.isVisible():
            QApplication.quit()

    # Evitar cerrar ventana durante instalación
    def closeEvent(self, event):
        # Cerrar durante una instalación solo oculta la ventana: la instalación sigue en segundo plano.
        if self.job is not None:
            self.hide(); event.ignore(); return
        super().closeEvent(event)


# Punto de entrada: abre la ventana del instalador
def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName('org.prosperus.Installer')
    from .appearance import speak_spanish; speak_spanish(app)
    window = Installer(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
