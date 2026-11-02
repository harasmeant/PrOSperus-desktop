# SPDX-License-Identifier: GPL-3.0-only
"""Instalar programas desde Fedora (dnf5) y Flathub (flatpak), o un .rpm/.flatpakref local."""
from pathlib import Path
import re
import sys

from PySide6.QtCore import QProcess, Qt
from .window_header import WindowHeader
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

SAFE = re.compile(r'^[\w .+-]+$')


def search_commands(text):
    term = text.strip()
    # Nunca pasa por un shell, pero una búsqueda rara no es un nombre de programa.
    if not term or not SAFE.match(term):
        return []
    return [('fedora', ['dnf5', '-q', '-C', 'repoquery', '--available', '--latest-limit=1',
                        '--queryformat=%{name}\t%{summary}\n', f'*{term}*']),
            ('flathub', ['flatpak', 'search', '--columns=application,name,description', term])]


def parse_dnf(output):
    found, seen = [], set()
    for line in output.splitlines():
        name, _, summary = line.partition('\t')
        if name.strip() and name not in seen:
            seen.add(name)
            found.append({'source': 'fedora', 'id': name.strip(), 'name': name.strip(), 'summary': summary.strip()})
    return found


def parse_flatpak(output):
    found = []
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) >= 2 and '.' in parts[0]:
            found.append({'source': 'flathub', 'id': parts[0].strip(), 'name': parts[1].strip(),
                          'summary': parts[2].strip() if len(parts) > 2 else ''})
    return found


def install_command(item):
    # shortcut: sudo -n usa el sudo sin contraseña de la imagen de desarrollo; usar pkexec en la de uso diario.
    if item['source'] == 'fedora':
        return ['sudo', '-n', 'dnf5', 'install', '-y', item['id']]
    if item['source'] == 'flathub':
        return ['sudo', '-n', 'flatpak', 'install', '-y', '--noninteractive', 'flathub', item['id']]
    path = str(item['id'])
    if path.lower().endswith('.rpm'):
        return ['sudo', '-n', 'dnf5', 'install', '-y', path]
    if path.lower().endswith('.flatpakref'):
        return ['sudo', '-n', 'flatpak', 'install', '-y', '--noninteractive', '--from', path]
    raise ValueError('Solo se instalan archivos .rpm o .flatpakref.')


STYLE = '''
QWidget { background: #1d231c; color: #e3e8da; font-family: 'DejaVu Sans'; font-size: 13px; }
QLabel#title { font-size: 20px; font-weight: bold; }
QLineEdit, QListWidget, QPlainTextEdit { background: #2a3328; border: 1px solid #4c5a48; border-radius: 10px; padding: 6px; }
QLineEdit { min-height: 30px; font-size: 15px; }
QListWidget::item { padding: 6px; border-radius: 8px; }
QListWidget::item:selected { border: 2px solid #9fc28a; background: #344030; }
QPushButton { background: #2a3328; border: 1px solid #4c5a48; border-radius: 8px; padding: 6px 14px; }
QPushButton:hover { background: #344030; }
'''


class Installer(QWidget):
    def __init__(self, path=None):
        super().__init__()
        self.setWindowTitle('Instalar programas'); self.resize(760, 560); self.setStyleSheet(STYLE)
        self.searches, self.results, self.job = [], {}, None
        layout = QVBoxLayout(self)
        layout.addWidget(WindowHeader('Instalar programas', self))
        self.search = QLineEdit(); self.search.setPlaceholderText('Busca un programa: blender, freecad, zen…')
        self.search.returnPressed.connect(self.run_search); layout.addWidget(self.search)
        self.list = QListWidget(); self.list.itemActivated.connect(lambda _: self.install()); layout.addWidget(self.list)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(120); layout.addWidget(self.log)
        row = QHBoxLayout(); row.addStretch()
        self.install_button = QPushButton('Instalar'); self.install_button.clicked.connect(lambda: self.install())
        close = QPushButton('Cerrar'); close.clicked.connect(self.close)
        row.addWidget(self.install_button); row.addWidget(close); layout.addLayout(row)
        if path:
            self.show_items([{'source': 'file', 'id': str(Path(path).resolve()), 'name': Path(path).name, 'summary': 'Archivo local'}])
        self.search.setFocus()

    def show_items(self, items):
        self.list.clear()
        for item in items:
            tag = {'fedora': '[Fedora]', 'flathub': '[Flathub]'}.get(item['source'], '[Archivo]')
            widget = QListWidgetItem(f"{tag}  {item['name']} — {item['summary']}")
            widget.setData(Qt.ItemDataRole.UserRole, item); self.list.addItem(widget)
        if self.list.count():
            self.list.setCurrentRow(0)

    def run_search(self):
        commands = search_commands(self.search.text())
        if not commands:
            self.log.setPlainText('Escribe un nombre de programa (letras, números, - _ . +).'); return
        self.results = {}; self.list.clear(); self.log.setPlainText('Buscando…')
        for source, argv in commands:
            process = QProcess(self); self.searches.append(process)
            process.finished.connect(lambda code, status, p=process, s=source: self.search_done(p, s))
            process.errorOccurred.connect(lambda error, p=process: self.failed(p, error))
            process.start(argv[0], argv[1:])

    def failed(self, process, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.log.appendPlainText('No está disponible: ' + process.program())
            self.search_done(process, None)

    def search_done(self, process, source):
        if process not in self.searches:
            return
        self.searches.remove(process)
        if source:
            output = bytes(process.readAllStandardOutput()).decode(errors='replace')
            self.results[source] = (parse_dnf if source == 'fedora' else parse_flatpak)(output)
            if process.exitCode() and not self.results[source]:
                self.log.appendPlainText(bytes(process.readAllStandardError()).decode(errors='replace').strip())
        process.deleteLater()
        items = self.results.get('fedora', []) + self.results.get('flathub', [])
        self.show_items(items)
        if not self.searches:
            self.log.appendPlainText(f'{len(items)} resultados.')

    def install(self):
        current = self.list.currentItem()
        if current is None or self.job is not None:
            return
        item = current.data(Qt.ItemDataRole.UserRole)
        try:
            argv = install_command(item)
        except ValueError as error:
            QMessageBox.warning(self, 'Instalar', str(error)); return
        if item['source'] == 'file' and QMessageBox.question(self, 'Instalar', f"¿Instalar {item['name']}?") != QMessageBox.StandardButton.Yes:
            return
        self.log.setPlainText('Instalando ' + item['name'] + '…')
        self.job = QProcess(self); self.job.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.job.readyReadStandardOutput.connect(lambda: self.log.appendPlainText(bytes(self.job.readAllStandardOutput()).decode(errors='replace').rstrip()))
        self.job.finished.connect(self.install_done)
        self.install_button.setEnabled(False)
        self.job.start(argv[0], argv[1:])

    def install_done(self, code, status):
        self.log.appendPlainText('Instalado.' if code == 0 and status == QProcess.ExitStatus.NormalExit else f'Error (código {code}).')
        self.job.deleteLater(); self.job = None; self.install_button.setEnabled(True)
        if not self.isVisible():
            QApplication.quit()

    def closeEvent(self, event):
        # Cerrar durante una instalación solo oculta la ventana: la instalación sigue en segundo plano.
        if self.job is not None:
            self.hide(); event.ignore(); return
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName('org.prosperus.Installer')
    window = Installer(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
