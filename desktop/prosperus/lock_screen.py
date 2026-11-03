# SPDX-License-Identifier: GPL-3.0-only
"""Pantalla de bloqueo con el fondo del proyecto desenfocado y los colores del tema.

`python3 -m prosperus.lock_screen` prepara la imagen y sustituye el proceso por swaylock
(Super+L, y swayidle al rato sin usar el equipo). Sin fondo publicado, bloquea con el color base.
lock_image la escribió qwen2.5-coder (local); se corrigió que oscurecía la imagen sin desenfocar."""
import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

from .theme_state import current_palette, state_dir


def lock_image(source, target, width=1920, height=1080):
    """Blurred, darkened copy of a wallpaper for the lock screen. Returns True if written."""
    image = QImage(str(source))
    if image.isNull():
        return False
    image = image.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                         Qt.TransformationMode.SmoothTransformation)
    image = image.copy((image.width() - width) // 2, (image.height() - height) // 2, width, height)
    # Desenfoque barato: reducir mucho y volver a ampliar, dos veces.
    for _ in range(2):
        small = image.scaled(width // 40, height // 40, Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        image = small.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    painter = QPainter(image)
    painter.fillRect(image.rect(), QColor(0, 0, 0, 90))
    painter.end()
    return image.save(str(target), 'PNG')


def swaylock_command(colors, image=None):
    """Orden de swaylock con el anillo y los textos en los colores del proyecto."""
    hexa = lambda value, alpha='ff': value.lstrip('#') + alpha
    # Sin --ignore-empty-password: el usuario Live no tiene contraseña e Intro desbloquea;
    # si se pone una con passwd, la pide.
    argv = ['swaylock', '--daemonize', '--show-failed-attempts',
            '--indicator-radius', '90', '--indicator-thickness', '8', '--font', 'DejaVu Sans',
            '--color', hexa(colors.base),
            '--inside-color', hexa(colors.base, 'aa'), '--ring-color', hexa(colors.border),
            '--key-hl-color', hexa(colors.accent), '--bs-hl-color', 'cc7870ff',
            '--line-color', '00000000', '--separator-color', '00000000',
            '--text-color', hexa(colors.text),
            '--inside-ver-color', hexa(colors.card, 'aa'), '--ring-ver-color', hexa(colors.accent),
            '--text-ver-color', hexa(colors.text),
            '--inside-wrong-color', 'cc7870aa', '--ring-wrong-color', 'cc7870ff',
            '--text-wrong-color', hexa(colors.text),
            '--inside-clear-color', hexa(colors.base, 'aa'), '--ring-clear-color', hexa(colors.muted),
            '--text-clear-color', hexa(colors.text)]
    if image:
        argv += ['--image', str(image), '--scaling', 'fill']
    return argv


def main():
    directory = state_dir()
    colors = current_palette(directory)
    image = None
    try:
        wallpaper = json.loads((directory / 'theme.json').read_text(encoding='utf-8')).get('wallpaper')
    except (OSError, TypeError, ValueError, AttributeError):
        wallpaper = None
    if wallpaper and Path(wallpaper).is_file():
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        app = QGuiApplication(sys.argv[:1])  # noqa: F841 - QImage/QPainter necesitan la aplicación
        target = directory / 'lock.png'
        if lock_image(wallpaper, target):
            image = target
    argv = swaylock_command(colors, image)
    os.execvp(argv[0], argv)


if __name__ == '__main__':
    main()
