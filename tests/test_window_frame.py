# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
"""Marco de las ventanas: color de resalte del fondo, filigrana y paleta compartida."""
import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from prosperus import theme_state
from prosperus.appearance import Palette
from prosperus.window_frame import attach_frame, paint_frame


class WindowFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def frame_image(self, colors, traits=None):
        image = QImage(400, 300, QImage.Format.Format_ARGB32); image.fill(0)
        painter = QPainter(image)
        paint_frame(painter, QRectF(1, 1, 398, 298), colors, traits, 12, 3)
        painter.end()
        return image

    def test_border_uses_accent_and_corners_get_filigree(self):
        colors = Palette(210)
        image = self.frame_image(colors)
        accent = QColor(colors.accent)
        edge = image.pixelColor(200, 1)
        self.assertGreater(edge.alpha(), 0)
        self.assertLess(abs(edge.hue() - accent.hue()) % 360, 20)
        # Filigrana dentro de las esquinas con adorno y nada en las otras dos.
        ink = lambda x0, y0: sum(image.pixelColor(x, y).alpha() > 0 for x in range(x0, x0 + 60) for y in range(y0, y0 + 40))
        self.assertGreater(ink(14, 8), 30)
        self.assertGreater(ink(326, 252), 30)
        self.assertEqual(ink(326, 8), 0)

    def test_other_wallpaper_other_colour(self):
        warm, cold = self.frame_image(Palette(40)), self.frame_image(Palette(210))
        self.assertNotEqual(warm.pixelColor(200, 1).name(), cold.pixelColor(200, 1).name())

    def test_attach_once_and_follow_resize(self):
        window = QDialog(); window.resize(300, 200)
        first = attach_frame(window, lambda: Palette(120))
        self.assertIs(attach_frame(window, lambda: Palette(10)), first)
        window.show(); window.resize(500, 320); self.app.processEvents()
        self.assertEqual(first.geometry(), window.rect())
        window.close()

    def test_traits_are_published_without_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            traits = {'straight': .7, 'magic': .1, 'seed': 4, 'auto': True,
                      'ornaments': [{'kind': 'imagen', 'path': Path('/x.png')}],
                      'branch_gradient': {'alpha_end': .5, 'light': 0, 'light_end': .2}}
            theme_state.publish(Palette(30), Path(tmp), Path(tmp), traits=traits)
            data = json.loads((Path(tmp) / 'theme.json').read_text(encoding='utf-8'))
            self.assertEqual(data['traits']['straight'], .7)
            self.assertNotIn('ornaments', data['traits'])
            self.assertNotIn('auto', data['traits'])
            self.assertEqual(theme_state.current_traits(Path(tmp))['branch_gradient']['light_end'], .2)
            self.assertIn('border-color=ff' + Palette(30).accent[1:], (Path(tmp) / 'foot.ini').read_text(encoding='utf-8'))
        self.assertIsNone(theme_state.current_traits(Path('/nonexistent')))


if __name__ == '__main__':
    unittest.main()


class FrameRoomTest(unittest.TestCase):
    def test_frame_leaves_room_for_corner_filigree(self):
        from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
        from prosperus.window_frame import MARGIN, attach_frame
        from prosperus.appearance import Palette
        app = QApplication.instance() or QApplication([])
        window = QWidget(); layout = QVBoxLayout(window); layout.setContentsMargins(4, 4, 4, 4)
        attach_frame(window, lambda: Palette())
        m = layout.contentsMargins()
        self.assertEqual((m.left(), m.right(), m.bottom()), (MARGIN, MARGIN, MARGIN))

    def test_arrows_are_svg_in_the_requested_colour(self):
        from pathlib import Path
        from prosperus.appearance import arrow
        for kind in ('down', 'up', 'check'):
            text = Path(arrow(kind, '#abcdef')).read_text()
            self.assertIn('#abcdef', text); self.assertIn('<svg', text)
