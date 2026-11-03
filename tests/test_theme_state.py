# SPDX-License-Identifier: GPL-3.0-only
import tempfile
import unittest
from pathlib import Path

from prosperus.appearance import Palette
from prosperus.theme_state import current_palette, foot_config, mako_config, publish


class ThemeStateTest(unittest.TestCase):
    def test_publish_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'prosperus'
            colors = Palette(207)
            publish(colors, Path('/home/prosperus/Proyectos/Laboratorio'), directory)
            self.assertEqual((directory / 'folder').read_text().strip(), '/home/prosperus/Proyectos/Laboratorio')
            again = current_palette(directory)
            self.assertEqual((again.base, again.accent), (colors.base, colors.accent))
            self.assertIn('background=' + colors.base[1:], (directory / 'foot.ini').read_text())

    def test_missing_state_gives_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(current_palette(Path(tmp)).base, Palette().base)

    def test_foot_includes_system_config(self):
        text = foot_config(Palette(30), base='/etc/xdg/foot/foot.ini')
        self.assertTrue(text.startswith('[main]\ninclude=/etc/xdg/foot/foot.ini'))

    def test_mako_keeps_other_lines(self):
        base = 'font=DejaVu Sans 11\nbackground-color=#1d231cee\ntext-color=#e3e8da\nborder-color=#9fc28a\n'
        colors = Palette(207)
        text = mako_config(colors, base)
        self.assertIn('font=DejaVu Sans 11', text)
        self.assertIn('background-color=' + colors.base + 'ee', text)
        self.assertNotIn('#9fc28a', text)


if __name__ == '__main__':
    unittest.main()
