# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import tempfile
import unittest
from pathlib import Path

from prosperus.screensaver import find_wallpapers, motion, timeline
from prosperus.window_session import SAVER_ID, targets


class TimelineTest(unittest.TestCase):
    def test_slides_follow_each_other_without_jumps(self):
        # Justo antes de cambiar, el siguiente fondo ya está entero y en el mismo punto de su movimiento.
        a, b, mix, _, progress_b = timeline(39.999)
        a2, b2, mix2, progress_a2, _ = timeline(40.0)
        self.assertEqual((a, b, a2, b2), (0, 1, 1, 2))
        self.assertAlmostEqual(mix, 1.0, places=3)
        self.assertEqual(mix2, 0.0)
        self.assertAlmostEqual(progress_b, progress_a2, places=3)

    def test_no_blend_in_the_middle(self):
        self.assertEqual(timeline(10)[2], 0.0)


class MotionTest(unittest.TestCase):
    def test_view_never_leaves_the_image(self):
        for index in range(30):
            for step in range(11):
                zoom, x, y = motion(index, step / 10)
                self.assertGreaterEqual(zoom, 1.05)
                reach = (1 - 1 / zoom) / 2
                self.assertLessEqual(abs(x), reach + 1e-9)
                self.assertLessEqual(abs(y), reach + 1e-9)

    def test_same_slide_moves_the_same_way(self):
        self.assertEqual(motion(4, 0.3), motion(4, 0.3))


class WallpapersTest(unittest.TestCase):
    def test_current_first_then_projects_without_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ('wallpaper.png', 'a/wallpaper.jpg', 'a/wallpaper-07.jpg', 'b/c/wallpaper.webp',
                        '.oculta/wallpaper.png', 'a/foto.png', 'a/.wallpaper-anterior.png'):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(b'x')
            (root / 'enlace').mkdir()
            (root / 'enlace' / 'wallpaper.png').symlink_to(root / 'wallpaper.png')
            found = find_wallpapers(root / 'a' / 'wallpaper.jpg', root)
            names = [str(p.relative_to(root)) for p in found]
            self.assertEqual(names[0], 'a/wallpaper.jpg')
            self.assertEqual(sorted(names), sorted(['a/wallpaper.jpg', 'wallpaper.png', 'a/wallpaper-07.jpg',
                                                    'b/c/wallpaper.webp']))

    def test_limit_and_missing(self):
        self.assertEqual(find_wallpapers(None, '/nonexistent'), [])


class WindowSessionTest(unittest.TestCase):
    def test_saver_is_never_arranged(self):
        # El escritorio organiza las ventanas nuevas; el salvapantallas debe seguir a pantalla completa.
        saver = {'type': 'con', 'id': 7, 'app_id': SAVER_ID, 'nodes': [], 'floating_nodes': []}
        app = {'type': 'con', 'id': 8, 'app_id': 'foot', 'nodes': [], 'floating_nodes': []}
        tree = {'type': 'root', 'nodes': [{'type': 'workspace', 'name': '1', 'nodes': [],
                                           'floating_nodes': [saver, app]}], 'floating_nodes': []}
        workspaces = [{'name': '1', 'output': 'eDP-1', 'visible': True,
                       'rect': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080}}]
        from prosperus.window_layouts import LayoutOptions
        placed = [identity for identity, _ in targets(tree, workspaces, 'eDP-1', LayoutOptions())]
        self.assertEqual(placed, [8])


if __name__ == '__main__':
    unittest.main()
