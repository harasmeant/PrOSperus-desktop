# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.pop('SWAYSOCK', None)
from pathlib import Path
import tempfile
import unittest
from PySide6.QtWidgets import QApplication
from prosperus.shell import Desktop


class NoteModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('uno', 'dos', 'tres'):
            (self.root / (name + '.md')).write_text('# ' + name)
        self.window = Desktop(self.root); self.window.resize(1920, 1080); self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def open(self, *names):
        for name in names:
            self.window.open_note(self.root / (name + '.md'))
        self.app.processEvents()
        return [self.window.panels[self.window.vault.checked(self.root / (n + '.md'))] for n in names]

    def test_fibonacci_mode_tiles_notes_without_overlap(self):
        self.assertEqual(self.window.windows.mode, 'fibonacci')
        a, b, c = self.open('uno', 'dos', 'tres')
        for p, q in [(a, b), (a, c), (b, c)]:
            self.assertFalse(p.geometry().intersects(q.geometry()))
        surface = self.window.surface.rect()
        self.assertTrue(all(surface.contains(p.geometry()) for p in (a, b, c)))

    def test_fullscreen_mode_fills_desktop_and_toggle_retiles(self):
        self.window.toggle_app_mode()
        self.assertEqual(self.window.windows.mode, 'fullscreen')
        (a,) = self.open('uno')
        self.assertEqual(a.geometry(), self.window.surface.rect())
        self.window.toggle_app_mode()
        self.assertNotEqual(a.geometry(), self.window.surface.rect())

    def test_maximize_button_restores_previous_size(self):
        (a,) = self.open('uno')
        before = a.geometry()
        a.toggle_maximized()
        self.assertEqual(a.geometry(), self.window.surface.rect())
        a.toggle_maximized()
        self.assertEqual(a.geometry(), before)


if __name__ == '__main__':
    unittest.main()
