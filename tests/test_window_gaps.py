# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import unittest

from prosperus.window_gaps import Splitter, commands_for, drag, find_splitter
from prosperus.window_layouts import LayoutOptions, Rect, arrange

AREA = Rect(0, 0, 1600, 1200)


def spiral(count, gap=12):
    return {i + 1: r for i, r in enumerate(arrange(AREA, count, LayoutOptions(gap=gap)))}


class GapTests(unittest.TestCase):
    def test_first_cut_moves_every_window_on_that_line(self):
        rects = spiral(4)
        gap_x = rects[1].x + rects[1].width + 6
        splitter = find_splitter(rects, gap_x, 600, 12)
        # La ventana grande a la izquierda; a la derecha, las que empiezan en ese borde (2 y 4), no la 3.
        self.assertEqual(splitter, Splitter(True, (1,), (2, 4)))
        moved = drag(rects, splitter, 100, AREA)
        self.assertEqual(moved[1].width, rects[1].width + 100)
        for i in (2, 4):
            self.assertEqual(moved[i].x, rects[i].x + 100)
            self.assertEqual(moved[i].x + moved[i].width, rects[i].x + rects[i].width)
        self.assertNotIn(3, moved)

    def test_horizontal_gap(self):
        rects = spiral(3)
        gap_y = rects[2].y + rects[2].height + 6
        splitter = find_splitter(rects, rects[2].x + 50, gap_y, 12)
        self.assertEqual(splitter, Splitter(False, (2,), (3,)))
        moved = drag(rects, splitter, -50, AREA)
        self.assertEqual(moved[2].height, rects[2].height - 50)
        self.assertEqual(moved[3].y, rects[3].y - 50)

    def test_drag_keeps_a_minimum_size(self):
        rects = spiral(2)
        splitter = find_splitter(rects, rects[1].width + 18, 500, 12)
        moved = drag(rects, splitter, 5000, AREA)
        self.assertEqual(moved[2].width, 200)
        moved = drag(rects, splitter, -5000, AREA)
        self.assertEqual(moved[1].width, 200)

    def test_outer_margin_resizes_one_side_within_the_screen(self):
        rects = {1: Rect(100, 100, 600, 400)}
        splitter = find_splitter(rects, 706, 300, 12)
        self.assertEqual(splitter, Splitter(True, (1,), ()))
        self.assertEqual(drag(rects, splitter, 5000, AREA)[1].width, 1500)

    def test_far_from_any_edge_is_not_a_gap(self):
        rects = {1: Rect(100, 100, 600, 400)}
        self.assertIsNone(find_splitter(rects, 900, 300, 12))
        # Cerca de la esquina pero fuera de la altura de la ventana.
        self.assertIsNone(find_splitter(rects, 706, 509, 12))

    def test_commands_use_ids_only(self):
        self.assertEqual(commands_for({7: Rect(1, 2, 300, 400)}),
                         '[con_id=7] resize set width 300 px height 400 px, move absolute position 1 px 2 px')


if __name__ == '__main__':
    unittest.main()


class GapControlTests(unittest.TestCase):
    """El filtro del escritorio con un árbol de Sway simulado."""

    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from pathlib import Path
        from unittest.mock import patch
        from prosperus.shell import Desktop
        self.window = Desktop(Path(__file__).resolve().parents[1] / 'demo-system')
        self.window.resize(1600, 1000); self.window.show(); self.app.processEvents()
        self.window.windows.available = True
        self.window.app_windows = [{'id': 1, 'name': 'a', 'hidden': False}, {'id': 2, 'name': 'b', 'hidden': False}]
        node = lambda i, x, w: {'id': i, 'type': 'floating_con', 'app_id': 'foot', 'name': 'foot',
                                'rect': {'x': x, 'y': 12, 'width': w, 'height': 976}, 'nodes': [], 'floating_nodes': []}
        self.tree = {'type': 'root', 'nodes': [{'type': 'workspace', 'name': 'General',
                     'rect': {'x': 0, 'y': 0, 'width': 1600, 'height': 1000}, 'nodes': [
                         {'id': 9, 'type': 'con', 'app_id': 'org.prosperus.Desktop', 'name': 'PrOSperus desktop',
                          'rect': {'x': 0, 'y': 0, 'width': 1600, 'height': 1000}, 'nodes': [], 'floating_nodes': []}],
                     'floating_nodes': [node(1, 12, 782), node(2, 806, 782)]}], 'floating_nodes': []}
        self.sent = []
        fake = lambda kind, payload='': self.tree if kind == 4 else self.sent.append(payload) or [{'success': True}]
        self.patch = patch('prosperus.window_gaps.request', fake); self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def test_drag_in_gap_resizes_both_windows(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        target = self.window.childAt(800, 300) or self.window
        point = target.mapFrom(self.window, QPoint(800, 300))
        QTest.mousePress(target, Qt.MouseButton.LeftButton, pos=point)
        QTest.mouseMove(target, point + QPoint(100, 0))
        QTest.mouseRelease(target, Qt.MouseButton.LeftButton, pos=point + QPoint(100, 0))
        self.assertTrue(self.sent, 'no se envió ninguna orden')
        self.assertIn('[con_id=1] resize set width 882 px', self.sent[-1])
        self.assertIn('[con_id=2] resize set width 682 px height 976 px, move absolute position 906 px', self.sent[-1])

    def test_double_click_on_background_minimizes(self):
        from unittest.mock import patch
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        target = self.window.childAt(800, 300) or self.window
        with patch.object(self.window.windows, 'minimize_all') as minimize:
            QTest.mouseDClick(target, Qt.MouseButton.LeftButton, pos=target.mapFrom(self.window, QPoint(800, 300)))
        minimize.assert_called_once()


class OutputTests(unittest.TestCase):
    def test_output_of_finds_nested_windows(self):
        from prosperus.window_manager import other_outputs, output_of
        tree = {'type': 'root', 'nodes': [
            {'type': 'output', 'name': 'A', 'nodes': [{'type': 'workspace', 'nodes': [], 'floating_nodes': [{'id': 5}]}]},
            {'type': 'output', 'name': 'B', 'nodes': [{'type': 'workspace', 'nodes': [{'id': 6, 'nodes': [{'id': 7}]}]}]}]}
        self.assertEqual(output_of(tree, 5), 'A')
        self.assertEqual(output_of(tree, 7), 'B')
        self.assertIsNone(output_of(tree, 8))
        self.assertEqual(other_outputs([{'name': 'A', 'active': True}, {'name': 'B', 'active': True},
                                        {'name': 'C', 'active': False}], 'A'), ['B'])
