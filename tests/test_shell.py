# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import unittest
from PySide6.QtWidgets import QApplication
from prosperus.shell import Desktop, STYLE


class ShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.root = Path(__file__).resolve().parents[1] / 'demo-system'
        self.window = Desktop(self.root)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.kiosk = False
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_project_note_minimize_restore_close(self):
        self.window.navigate(self.root / 'Bienvenida')
        self.window.open_note(self.root / 'Bienvenida/Empieza aquí.md')
        panel = next(iter(self.window.panels.values()))
        self.assertTrue(panel.isVisible())
        self.assertTrue(panel.reader.isReadOnly())
        self.assertIn('Bienvenido', panel.reader.toPlainText())
        panel.minimize()
        self.assertFalse(panel.isVisible())
        panel.restore()
        self.assertTrue(panel.isVisible())
        panel.close_note()
        self.assertFalse(self.window.panels)
        self.assertTrue(self.window.isVisible())

    def test_project_visibility_and_search(self):
        self.window.navigate(self.root / 'Laboratorio')
        self.window.open_first_note()
        panel = next(iter(self.window.panels.values()))
        self.window.navigate(self.root / 'Cuaderno')
        self.assertFalse(panel.isVisible())
        self.window.navigate(self.root / 'Laboratorio')
        self.assertTrue(panel.isVisible())
        self.window.search.setText('hipotesis')
        self.assertEqual([node.path.name for node in self.window.surface.nodes], ['Hipótesis.md', 'Plan de trabajo.md'])

    def test_kiosk_and_host_power_controls(self):
        self.window.kiosk = True
        self.window.close()
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.system_session)
        self.window.power('poweroff')  # Must be a no-op in local preview.


if __name__ == '__main__':
    unittest.main()
