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

    def test_arrows_work_on_the_map_right_after_start(self):
        # En la ISO de Debian el foco caía en el QScrollArea y las flechas no hacían nada.
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.assertIs(self.window.focusWidget(), self.window.surface)
        QTest.keyClick(self.window.surface, Qt.Key.Key_Right)
        self.assertEqual(len(self.window.surface.selection), 1)

    def test_tab_and_arrows_share_one_selection(self):
        # En el portátil, Tab movía el foco a otra tarjeta sin mover la selección
        # de las flechas: salían dos tarjetas resaltadas a la vez.
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        surface = self.window.surface
        QTest.keyClick(surface, Qt.Key.Key_Right)
        for _ in range(3):
            QTest.keyClick(self.window.focusWidget(), Qt.Key.Key_Tab)
            focused = self.window.focusWidget()
            highlighted = [n for n in surface.nodes if n.path in surface.selection or n.hasFocus()]
            if focused in surface.nodes:
                self.assertEqual(surface.selection, [focused.path])
                self.assertEqual(highlighted, [focused])

    def test_escape_goes_back_one_folder(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        folder = next(p for p in self.root.iterdir() if p.is_dir() and any(c.is_dir() for c in p.iterdir()))
        self.window.navigate(folder)
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        self.assertEqual(self.window.folder, self.root)

    def test_only_one_card_highlighted_after_hover_and_arrows(self):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QEnterEvent
        from PySide6.QtTest import QTest
        surface = self.window.surface
        first, second = surface.nodes[0], surface.nodes[1]
        QTest.keyClick(surface, Qt.Key.Key_Right)
        selected = surface.selection[0]
        other = second if first.path == selected else first
        QApplication.sendEvent(other, QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(5, 5)))
        self.app.processEvents()
        self.assertEqual(surface.selection, [other.path])
        self.assertTrue(other.hasFocus())

    def test_kiosk_and_host_power_controls(self):
        self.window.kiosk = True
        self.window.close()
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.system_session)
        self.window.power('poweroff')  # Must be a no-op in local preview.


if __name__ == '__main__':
    unittest.main()
