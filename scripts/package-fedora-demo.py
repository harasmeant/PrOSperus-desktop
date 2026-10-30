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
NAME = 'prosperus-demo-v4'

LAUNCHER = (REPO / 'desktop/iniciar.sh').read_text()

LIVE_LAUNCHER = '''#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if [ ! -x /tmp/prosperus-runtime/bin/python ]; then
    printf '%s\\n' 'Prepara primero el entorno temporal siguiendo LEEME.txt (Fedora Live).'
    exit 1
fi
export PROSPERUS_PYTHON=/tmp/prosperus-runtime/bin/python
exec sh ./iniciar.sh "$@"
'''

README = '''PrOSperus desktop 0.4.0-dev — demo para Fedora

1. Extrae prosperus-demo-v4.tar.gz dentro de Fedora.
2. Entra en la carpeta prosperus-demo-v4 donde está iniciar.sh.
3. Abre una terminal en esa carpeta y ejecuta:

   sh iniciar.sh

Si ya tienes las dependencias, basta con sh iniciar.sh. Si el Python de Fedora
no tiene PySide6, el lanzador detecta automáticamente el entorno ligero que
hayas preparado en /tmp/prosperus-runtime y comprueba que funciona antes de usarlo.
No entres en la subcarpeta prosperus: contiene el código, no el lanzador.
Si faltan dependencias en Fedora Live, usa la alternativa ligera descrita abajo.
En Fedora instalado, con espacio suficiente, puedes instalarlas con:

   sudo dnf install --setopt=install_weak_deps=False python3-pyside6 qt6-qtwayland python3-gobject

SI FALLA LA INSTALACIÓN POR ESPACIO

Fedora Live puede tener un espacio de escritura en / mucho menor que el disco
virtual de Boxes. Si DNF dice 'needs more space on the / filesystem', no ha
terminado de instalar las dependencias. Repetir iniciar.sh no lo corrige.
Comprueba el espacio ejecutando esta línea sola:

   df -h / /var/cache /tmp

Una segunda comprobación, por separado, muestra la caché de descargas:

   sudo du -sh /var/cache/libdnf5

DNF5 permite usar una caché temporal en otro sistema de archivos con espacio
mediante --setopt=system_cachedir=RUTA. Eso no amplía el espacio para los paquetes
instalados en /. Si sigue faltando espacio, usa Fedora instalado en el disco
virtual; conserva primero tus notas fuera de la sesión Live.

ALTERNATIVA LIGERA PARA FEDORA LIVE

Con espacio libre en /tmp, puedes usar los módulos básicos de Qt sin instalar
el paquete completo de Fedora en /. Ejecuta cada línea por separado:

   python3 -m venv --system-site-packages /tmp/prosperus-runtime

   /tmp/prosperus-runtime/bin/python -m pip install --no-cache-dir --only-binary=:all: PySide6-Essentials

   sh iniciar.sh

La descarga requiere Internet. El entorno está en /tmp y se pierde al reiniciar;
tendrás que prepararlo de nuevo. Las notas siguen guardándose en proyectos/.
Para abrir proyectos de otra copia, localiza primero su carpeta proyectos
y pasa su ruta real con --root. No presupongas que existe una carpeta v3.
Si tus proyectos están en esta copia, basta con sh iniciar.sh.

Para Aplicaciones se usan los módulos GIO que tenga instalados Fedora.
Esta alternativa evita la instalación completa de Qt, pero requiere las
bibliotecas gráficas y una sesión de escritorio del sistema anfitrión.

QUÉ PROBAR

- Doble clic en Bienvenida; hay ocho tarjetas sobre el fondo botánico de la demo.
- Carpetas: rueda/flechas para recorrer portadas, Intro o clic para abrir.
- Fijar mantiene el tarjetero abierto; sin fijarlo, salir lo recoge.
- Laboratorio y Cuaderno tienen su propio fondo y paleta.
- Las subcarpetas heredan el fondo del proyecto.
- Abre dos notas, mueve y redimensiona; minimiza y recupera desde la barra.
- Editar permite escribir Markdown; Ctrl+S guarda y Vista previa lo muestra.
- Nuevo proyecto crea un espacio en Tus proyectos. Carpetas > Importar proyecto
  copia una carpeta existente, conservando sus notas, subcarpetas y adjuntos.
- Un clic selecciona, Ctrl+clic selecciona varios y doble clic o Intro abre.
- Ctrl+C/Ctrl+V copia y pega; Ctrl+D duplica. Clic derecho ofrece más acciones.
- Puedes copiar desde Archivos de Fedora o arrastrar notas/carpetas al mapa.
- Explorar incluye copiar, pegar e importar. Los nombres repetidos añaden
  ' - copia'; nunca se sobrescriben los originales.
- Aplicaciones busca programas de Fedora; Fijar añade favoritos globales.
- Los buscadores del mapa, Explorar y Carpetas encuentran nombres y contenido
  guardado de los .md, incluyendo subcarpetas, sin distinguir tildes/mayúsculas.
  Todos los términos deben coincidir en el nombre/ruta o texto de una nota.
  Los archivos ilegibles o mayores de 2 MiB siguen disponibles por nombre.
- Ctrl+Espacio abre Aplicaciones. F1 muestra los atajos y F11 pantalla completa.
- Windows/Super abre Aplicaciones solo si el sistema entrega esa tecla a
  PrOSperus. GNOME la reserva para Actividades, incluso a pantalla completa.
- Controles ofrece volumen, reproducción y brillo según la sesión y hardware.
  Herramientas opcionales en Fedora: sudo dnf install wireplumber playerctl brightnessctl
  No suele haber control de brillo dentro de una VM.
- Controles > Pantallas y distribución ofrece espiral Fibonacci, columnas y
  principal centrada, con vista previa, separación y anchura máxima centrada.
  Guarda perfiles estándar, 21:9 y 32:9. Organizar notas permite deshacer.
  No cambia resolución ni escala. Organizar aplicaciones requiere Sway y es
  experimental; GNOME y la ISO actual con Cage no ofrecen esa integración.
  Se aplica al pulsar el botón, sin reorganización automática ni deshacer
  para aplicaciones. Más información en DISTRIBUCION.md.

Estas notas son ejemplos: edítalas libremente. El paquete no contiene notas
personales, ajustes de Obsidian ni catálogos de aplicaciones del anfitrión.
Las aplicaciones se abren con sus permisos habituales dentro de Fedora.
Las copias conservan los enlaces escritos; no reescriben rutas entre carpetas.
No se importan enlaces simbólicos ni archivos especiales. El mapa muestra
carpetas y notas Markdown; los adjuntos de los proyectos sí se conservan.

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
        shutil.copy2(REPO / 'docs/WINDOW-LAYOUTS.md', bundle / 'DISTRIBUCION.md')
        (bundle / 'iniciar.sh').write_text(LAUNCHER)
        (bundle / 'iniciar.sh').chmod(0o755)
        (bundle / 'iniciar-live.sh').write_text(LIVE_LAUNCHER)
        (bundle / 'iniciar-live.sh').chmod(0o755)
        (bundle / 'LEEME.txt').write_text(README)
        with tarfile.open(archive, 'w:gz') as target:
            target.add(bundle, arcname=NAME)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + '.sha256').write_text(digest + '  ' + archive.name + '\n')
    print(f'{archive}\n{archive.stat().st_size:,} bytes\nSHA256 {digest}')


if __name__ == '__main__':
    main()
