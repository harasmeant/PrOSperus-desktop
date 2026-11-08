# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import tempfile
import unittest
from pathlib import Path

from prosperus.appearance import Palette
from prosperus.theme_state import current_palette, kitty_config, mako_config, publish, wob_config


class ThemeStateTest(unittest.TestCase):
    def test_publish_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'prosperus'
            colors = Palette(207)
            publish(colors, Path('/home/prosperus/Proyectos/Laboratorio'), directory)
            self.assertEqual((directory / 'folder').read_text().strip(), '/home/prosperus/Proyectos/Laboratorio')
            again = current_palette(directory)
            self.assertEqual((again.base, again.accent), (colors.base, colors.accent))
            self.assertIn('background ' + colors.base, (directory / 'kitty.conf').read_text())

    def test_missing_state_gives_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(current_palette(Path(tmp)).base, Palette().base)

    def test_kitty_includes_system_config(self):
        text = kitty_config(Palette(30), base='/etc/xdg/kitty/kitty.conf')
        self.assertTrue(text.startswith('include /etc/xdg/kitty/kitty.conf\n'))
        self.assertIn('background ' + Palette(30).base, text)

    def test_wob_uses_palette(self):
        colors = Palette(207)
        text = wob_config(colors, (0, 15))  # versión fija: no depender del wob instalado
        self.assertIn('border_color = ' + colors.accent[1:] + 'ff', text)
        self.assertIn('[style.muted]', text)
        self.assertIn('output_mode', wob_config(colors, (0, 15)))
        self.assertNotIn('output_mode', wob_config(colors, (0, 16)))
        # Debian 13: wob 0.14 no conoce los estilos.
        self.assertNotIn('[style.muted]', wob_config(colors, (0, 14)))

    def test_mako_keeps_other_lines(self):
        base = 'font=DejaVu Sans 11\nbackground-color=#1d231cee\ntext-color=#e3e8da\nborder-color=#9fc28a\n'
        colors = Palette(207)
        text = mako_config(colors, base)
        self.assertIn('font=DejaVu Sans 11', text)
        self.assertIn('background-color=' + colors.base + 'ff', text)
        self.assertNotIn('#9fc28a', text)


if __name__ == '__main__':
    unittest.main()
