# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
from pathlib import Path
import tempfile
import unittest

from PySide6.QtWidgets import QApplication

from prosperus import hidden_items
from prosperus.shell import Desktop


class HiddenItemsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / 'A').mkdir(); (self.folder / 'B').mkdir()

    def test_hide_and_unhide_keep_files(self):
        hidden_items.hide(self.folder, [self.folder / 'A'])
        self.assertEqual(hidden_items.hidden_names(self.folder), {'A'})
        self.assertTrue((self.folder / 'A').is_dir())
        hidden_items.unhide(self.folder, [self.folder / 'A'])
        self.assertEqual(hidden_items.hidden_names(self.folder), set())
        self.assertFalse((self.folder / hidden_items.FILE).exists())

    def test_ignores_paths_from_other_folders_and_broken_files(self):
        hidden_items.hide(self.folder, [Path('/otra/sitio/A')])
        self.assertEqual(hidden_items.hidden_names(self.folder), set())
        (self.folder / hidden_items.FILE).write_text('{roto')
        self.assertEqual(hidden_items.hidden_names(self.folder), set())


class DesktopHiddenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'projects'; self.root.mkdir()
        self.project = self.root / 'Proyecto'; self.project.mkdir()
        (self.project / 'Visible').mkdir(); (self.project / 'Secreta').mkdir()
        self.window = Desktop(self.root)
        self.window.navigate(self.project)

    def names(self):
        return {node.path.name for node in self.window.surface.nodes}

    def menu_texts(self, paths):
        menu = self.window.files.menu(self.window.surface, paths, self.project, desktop=True)
        texts = [a.text() for a in menu.actions()]; menu.deleteLater()
        return texts

    def test_hide_from_menu_and_show_hidden_toggle(self):
        secret = self.project / 'Secreta'
        self.assertIn('Ocultar del escritorio', self.menu_texts([secret]))
        self.window.hide_from_desktop([secret])
        self.assertEqual(self.names(), {'Visible'})
        self.assertIn('Mostrar ocultos (1)', self.menu_texts([]))
        self.window.toggle_show_hidden()
        self.assertEqual(self.names(), {'Visible', 'Secreta'})
        node = next(n for n in self.window.surface.nodes if n.path == secret)
        self.assertTrue(node.hidden)
        self.assertIn('Volver a mostrar en el escritorio', self.menu_texts([secret]))
        self.window.show_on_desktop([secret]); self.window.toggle_show_hidden()
        self.assertEqual(self.names(), {'Visible', 'Secreta'})

    def test_explorer_menu_has_no_desktop_options(self):
        menu = self.window.files.menu(None, [self.project / 'Secreta'], self.project)
        self.assertNotIn('Ocultar del escritorio', [a.text() for a in menu.actions()])


if __name__ == '__main__':
    unittest.main()
