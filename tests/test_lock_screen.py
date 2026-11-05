# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import tempfile
import unittest
from pathlib import Path

from PySide6.QtGui import QColor, QGuiApplication, QImage

from prosperus.appearance import Palette
from prosperus.lock_screen import lock_image, swaylock_command


class LockScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def test_lock_image_is_blurred_and_sized(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'w.png'; target = Path(tmp) / 'l.png'
            image = QImage(400, 200, QImage.Format.Format_RGB32); image.fill(QColor('white'))
            for x in range(200):
                for y in range(200):
                    image.setPixelColor(x, y, QColor('black'))
            image.save(str(source))
            self.assertTrue(lock_image(source, target, 320, 180))
            out = QImage(str(target))
            self.assertEqual((out.width(), out.height()), (320, 180))
            # El borde blanco/negro queda difuminado: el centro es gris, no uno de los dos.
            self.assertTrue(20 < QColor(out.pixel(160, 90)).value() < 200)

    def test_missing_wallpaper(self):
        self.assertFalse(lock_image('/nonexistent.png', '/tmp/x.png'))

    def test_command_uses_palette(self):
        colors = Palette(207)
        argv = swaylock_command(colors, '/run/x/lock.png')
        self.assertEqual(argv[argv.index('--ring-ver-color') + 1], colors.accent[1:] + 'ff')
        self.assertIn('/run/x/lock.png', argv)
        self.assertNotIn('--image', swaylock_command(colors))


if __name__ == '__main__':
    unittest.main()
