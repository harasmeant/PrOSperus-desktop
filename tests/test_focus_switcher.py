# SPDX-License-Identifier: GPL-3.0-only
import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from prosperus.appearance import Palette
from prosperus.focus_trap import cycle_focus
from prosperus.window_switcher import WindowSwitcher

app = QApplication.instance() or QApplication([])


class FocusTrapTests(unittest.TestCase):
    def test_tab_wraps_inside_the_panel_and_skips_the_desktop(self):
        window = QWidget(); layout = QVBoxLayout(window)
        outside = QPushButton('mapa'); layout.addWidget(outside)
        panel = QWidget(); inner = QVBoxLayout(panel); layout.addWidget(panel)
        first, second = QPushButton('Editar'), QPushButton('Guardar')
        inner.addWidget(first); inner.addWidget(second)
        window.show(); window.activateWindow(); app.processEvents()
        second.setFocus(); app.processEvents()
        self.assertTrue(cycle_focus(panel, True))
        self.assertIs(QApplication.focusWidget(), first)
        self.assertTrue(cycle_focus(panel, False))
        self.assertIs(QApplication.focusWidget(), second)
        window.close()


class SwitcherTests(unittest.TestCase):
    def test_alt_tab_starts_on_the_previous_window_and_cycles(self):
        items = [{'name': 'Foot', 'hidden': False}, {'name': 'Nota', 'hidden': True}, {'name': 'Firefox', 'hidden': True}]
        switcher = WindowSwitcher(); chosen = []
        switcher.chosen.connect(chosen.append)
        switcher.step(items, 1, Palette(120))
        self.assertEqual(switcher.index, 1)
        self.assertIn('minimizada', switcher.caption.text())
        switcher.step(items, 1, None); switcher.step(items, 1, None)
        self.assertEqual(switcher.index, 0)
        switcher.step(items, -1, None)
        switcher.pick(switcher.index)
        self.assertEqual(chosen, [items[2]])
        self.assertFalse(switcher.isVisible())


if __name__ == '__main__':
    unittest.main()
