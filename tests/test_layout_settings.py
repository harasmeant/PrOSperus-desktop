# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from prosperus.shell import Desktop
from prosperus.layout_settings import LayoutDialog


class LayoutSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name in ('uno', 'dos'):
            (root / (name + '.md')).write_text('# ' + name)
        self.window = Desktop(root); self.window.resize(1920, 1080); self.window.show()
        for name in ('uno', 'dos'):
            self.window.open_note(root / (name + '.md'))
        self.app.processEvents()
        self.settings = QSettings(str(root / 'settings.ini'), QSettings.Format.IniFormat)
        self.dialog = LayoutDialog(self.window, self.settings)

    def tearDown(self):
        self.dialog.reject(); self.dialog.deleteLater()
        self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def test_arrange_and_undo_keep_note_content(self):
        panels = list(self.window.panels.values())
        geometry = [p.geometry() for p in panels]
        panels[0].editor.setPlainText('cambios sin guardar')
        self.dialog.apply_notes()
        self.assertTrue(self.dialog.undo.isEnabled())
        self.assertFalse(panels[0].geometry().intersects(panels[1].geometry()))
        self.dialog.undo_notes()
        self.assertEqual([p.geometry() for p in panels], geometry)
        self.assertEqual(panels[0].editor.toPlainText(), 'cambios sin guardar')
        panels[0].editor.setPlainText(panels[0].original)

    def test_profile_values_are_independent_and_saved(self):
        self.dialog.profile.setCurrentIndex(1)
        self.dialog.mode.setCurrentIndex(2); self.dialog.gap.setValue(24)
        self.dialog.width_limit.setValue(2400); self.dialog.save_profile()
        self.dialog.profile.setCurrentIndex(0)
        self.assertEqual(self.dialog.gap.value(), 12)
        self.dialog.profile.setCurrentIndex(1)
        self.assertEqual(self.dialog.gap.value(), 24)
        self.assertEqual(self.dialog.mode.currentData(), 'centered')
        self.assertEqual(self.settings.value('layouts/profiles/ultrawide/max_width', type=int), 2400)

    def test_failed_layout_does_not_move_notes(self):
        before = [p.geometry() for p in self.window.panels.values()]
        self.dialog.width_limit.setValue(100)
        self.dialog.apply_notes()
        self.assertEqual([p.geometry() for p in self.window.panels.values()], before)
        self.assertFalse(self.dialog.undo.isEnabled())
