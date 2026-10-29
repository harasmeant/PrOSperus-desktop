#!/usr/bin/env python3
"""Package the standalone desktop and clean demo data for Fedora Live."""
# SPDX-License-Identifier: GPL-3.0-only
import hashlib
from pathlib import Path
import shutil
import tarfile
import tempfile

REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / 'out'
NAME = 'prosperus-demo-v2'

LAUNCHER = '''#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if ! /usr/bin/python3 -c 'from PySide6.QtWidgets import QApplication' >/dev/null 2>&1; then
    printf '%s\\n' 'Faltan dependencias. Ejecuta dentro de Fedora:' 'sudo dnf install --setopt=install_weak_deps=False python3-pyside6 qt6-qtwayland python3-gobject'
    exit 1
fi
if ! /usr/bin/python3 -c 'import gi' >/dev/null 2>&1; then
    printf '%s\\n' 'El escritorio funcionará. Para usar Aplicaciones instala: sudo dnf install python3-gobject'
fi
exec /usr/bin/python3 -m prosperus --root "$PWD/proyectos"
'''

README = '''PrOSperus desktop 0.2.0-dev — demo para Fedora

1. Extrae prosperus-demo-v2.tar.gz dentro de Fedora.
2. Entra en la carpeta prosperus-demo-v2 donde está iniciar.sh.
3. Abre una terminal en esa carpeta y ejecuta:

   sudo dnf install --setopt=install_weak_deps=False python3-pyside6 qt6-qtwayland python3-gobject
   sh iniciar.sh

Si ya tienes las dependencias, basta con sh iniciar.sh.
No entres en la subcarpeta prosperus: contiene el código, no el lanzador.

QUÉ PROBAR

- Abre Bienvenida; hay ocho tarjetas sobre el fondo botánico de la demo.
- Carpetas: rueda/flechas para recorrer portadas, Intro o clic para abrir.
- Fijar mantiene el tarjetero abierto; sin fijarlo, salir lo recoge.
- Laboratorio y Cuaderno tienen su propio fondo y paleta.
- Las subcarpetas heredan el fondo del proyecto.
- Abre dos notas, mueve y redimensiona; minimiza y recupera desde la barra.
- Editar permite escribir Markdown; Ctrl+S guarda y Vista previa lo muestra.
- Crea una nota o carpeta. Explorar permite navegar y buscar.
- Aplicaciones busca programas de Fedora; Fijar añade favoritos globales.

Estas notas son ejemplos: edítalas libremente. El paquete no contiene notas
personales, ajustes de Obsidian ni catálogos de aplicaciones del anfitrión.
Las aplicaciones se abren con sus permisos habituales dentro de Fedora.

En Fedora Live los cambios no sobreviven al apagado: copia tus notas fuera
de la sesión si deseas conservarlas. El paquete nuevo es independiente de
la demo anterior; no borres archivos que hayas escrito en aquella.

PENDIENTES

Paridad de renombrado/movido/eliminación y actualización de enlaces con
Obsidian; edición visual; recuperar ventanas tras cerrar; aplicaciones
como nodos e integración del escritorio completo. Esta demo abre una
ventana en Fedora y no cambia su sesión ni su arranque.
'''


def main():
    OUTPUT.mkdir(exist_ok=True)
    archive = OUTPUT / (NAME + '.tar.gz')
    with tempfile.TemporaryDirectory(prefix='package-', dir=OUTPUT) as temporary:
        bundle = Path(temporary) / NAME
        bundle.mkdir()
        shutil.copytree(REPO / 'desktop/prosperus', bundle / 'prosperus',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(REPO / 'demo-system', bundle / 'proyectos')
        shutil.copy2(REPO / 'LICENSE', bundle / 'LICENSE')
        shutil.copy2(REPO / 'docs/DEMO-ASSETS.md', bundle / 'FONDOS.md')
        (bundle / 'iniciar.sh').write_text(LAUNCHER)
        (bundle / 'iniciar.sh').chmod(0o755)
        (bundle / 'LEEME.txt').write_text(README)
        with tarfile.open(archive, 'w:gz') as target:
            target.add(bundle, arcname=NAME)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + '.sha256').write_text(digest + '  ' + archive.name + '\n')
    print(f'{archive}\n{archive.stat().st_size:,} bytes\nSHA256 {digest}')


if __name__ == '__main__':
    main()
