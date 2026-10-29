"""Explain dependency failures before importing the graphical desktop."""
# SPDX-License-Identifier: GPL-3.0-only
import importlib
from pathlib import Path
import shutil
import sys

INSTALL_COMMAND = ('sudo dnf install --setopt=install_weak_deps=False '
                   'python3-pyside6 qt6-qtwayland python3-gobject')


def live_session():
    try:
        cmdline = Path('/proc/cmdline').read_text()
    except OSError:
        return False
    return 'root=live:' in cmdline or 'rd.live.image' in cmdline


def dependency_diagnostic(error):
    lines = ['No se pudo cargar la interfaz de PrOSperus.',
             f'Detalle: {type(error).__name__}: {error}']
    try:
        free = shutil.disk_usage('/').free // (1024 * 1024)
        lines.append(f'Espacio disponible en /: {free} MiB.')
    except OSError:
        lines.append('No se pudo consultar el espacio disponible.')
    if live_session():
        lines.extend([
            'Estás en Fedora Live: el espacio para instalar paquetes puede ser',
            'mucho menor que el disco virtual configurado en Boxes.',
            '',
            'Si preparaste el entorno ligero antes de reiniciar, /tmp se ha',
            'vaciado. Puedes volver a prepararlo con estas líneas, por separado:',
            'python3 -m venv --system-site-packages /tmp/prosperus-runtime',
            '/tmp/prosperus-runtime/bin/python -m pip install --no-cache-dir --only-binary=:all: PySide6-Essentials',
            'Después ejecuta: sh iniciar.sh',
        ])
    lines.extend([
        '',
        'Si DNF indicó "needs more space" o "No space left", la instalación',
        'no se completó. Repetir iniciar.sh no instala las dependencias.',
        'Comprueba el espacio con: df -h / /var/cache /tmp',
        'Consulta LEEME.txt antes de volver a instalar en una sesión Live.',
        '',
        'En Fedora con espacio suficiente, instala las dependencias con:',
        INSTALL_COMMAND,
    ])
    return '\n'.join(lines)


def main():
    try:
        importlib.import_module('PySide6.QtWidgets')
    except (ImportError, OSError) as error:
        print(dependency_diagnostic(error), file=sys.stderr)
        return 1
    try:
        importlib.import_module('gi')
    except (ImportError, OSError):
        print('Para usar Aplicaciones instala: sudo dnf install python3-gobject', file=sys.stderr)
    from .shell import main as desktop_main
    desktop_main()
    return 0


if __name__ == '__main__':
    sys.exit(main())
