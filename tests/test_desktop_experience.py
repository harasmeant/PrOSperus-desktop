# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from prosperus.appearance import palette_for, wallpaper_for
from prosperus.launcher import ApplicationBrowser, ApplicationService
from prosperus.shell import Desktop, Explorer


class DesktopExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'projects'; self.root.mkdir()
        for name in ('Bienvenida', 'Cuaderno', 'Laboratorio'):
            folder = self.root / name; folder.mkdir()
            (folder / 'Nota.md').write_text('# Nota\n\nContenido de ejemplo.')
        (self.root / 'Laboratorio/Apuntes').mkdir()
        (self.root / 'Laboratorio/Apuntes/Hipótesis.md').write_text('# Hipótesis\nIdea.')
        pixmap = QPixmap(40, 30); pixmap.fill(Qt.GlobalColor.darkGreen)
        pixmap.save(str(self.root / 'wallpaper.png'))
        self.window = Desktop(self.root)
        self.window.show(); self.app.processEvents()

    def tearDown(self):
        for panel in self.window.panels.values():
            panel.editor.setPlainText(panel.original)
        self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def test_browsing_covers_does_not_navigate_until_opened(self):
        self.window.navigate(self.root / 'Bienvenida')
        self.window.drawer.reveal()
        self.window.drawer.step(1)
        self.assertEqual(self.window.folder, self.root / 'Bienvenida')
        self.window.drawer.open_current()
        self.assertEqual(self.window.folder, self.root / 'Cuaderno')
        self.assertFalse(self.window.drawer.isVisible())

    def test_cover_filter_wrap_and_pin(self):
        drawer = self.window.drawer
        drawer.reveal(); drawer.step(-1)
        self.assertEqual(drawer.index, 2)
        drawer.search.setText('laboratorio')
        self.assertEqual(drawer.filtered, [self.root / 'Laboratorio'])
        drawer.set_pinned(True); drawer.open_current()
        self.assertTrue(drawer.isVisible())
        drawer.search.setText('sin resultados')
        self.assertEqual(drawer.stack.cards, [])
        drawer.open_current()
        self.assertEqual(self.window.folder, self.root / 'Laboratorio')

    def test_arrow_keys_on_cover_and_enter_open_project(self):
        drawer = self.window.drawer
        drawer.reveal(); self.app.processEvents()
        front = next(card for card in drawer.stack.cards if card.offset == 0)
        front.setFocus()
        QTest.keyClick(front, Qt.Key.Key_Down)
        self.assertEqual(drawer.index, 1)
        self.assertEqual(self.window.folder, self.root)
        QTest.keyClick(drawer.stack, Qt.Key.Key_Return)
        self.assertEqual(self.window.folder, self.root / 'Cuaderno')

    def test_dock_scrolls_instead_of_compressing_long_names(self):
        folder = self.root / 'Cuaderno'
        for index in range(15):
            (folder / f'Una nota de prueba bastante larga {index}.md').write_text('# Ejemplo')
        self.window.resize(900, 650); self.window.navigate(folder); self.app.processEvents()
        self.assertGreater(self.window.dock_content.width(), self.window.dock_scroll.viewport().width())
        self.assertGreater(self.window.dock_scroll.horizontalScrollBar().maximum(), 0)
        for item in self.window.dock_content.findChildren(QPushButton):
            if item.isHidden():
                continue
            icon_width = item.iconSize().width() + 8 if not item.icon().isNull() else 0
            self.assertLessEqual(item.fontMetrics().horizontalAdvance(item.text()) + 28 + icon_width, item.width())
        for node in self.window.surface.nodes:
            self.assertFalse(node.geometry().intersects(self.window.surface.center.geometry()))

    def test_wallpaper_inheritance_and_external_symlink_rejection(self):
        folder = self.root / 'Laboratorio/Apuntes'
        self.assertEqual(wallpaper_for(self.window.vault, folder), self.root / 'wallpaper.png')
        local = self.root / 'Laboratorio/wallpaper.png'
        local.write_bytes((self.root / 'wallpaper.png').read_bytes())
        self.assertEqual(wallpaper_for(self.window.vault, folder), local)
        external = Path(self.temp.name) / 'private.png'; external.write_bytes(local.read_bytes())
        (folder / 'wallpaper.png').symlink_to(external)
        self.assertEqual(wallpaper_for(self.window.vault, folder), local)
        self.assertEqual(palette_for(self.window.vault, folder).accent, palette_for(self.window.vault, local.parent).accent)

    def test_edit_save_and_unsaved_close_cancel(self):
        note = self.root / 'Bienvenida/Nota.md'
        self.window.navigate(note.parent); self.window.open_note(note)
        panel = self.window.panels[note]
        panel.toggle_edit(); panel.editor.setPlainText('# Nueva nota\nTexto editado.')
        self.assertTrue(panel.dirty)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel):
            panel.close_note()
        self.assertIn(note, self.window.panels)
        self.assertTrue(panel.save())
        self.assertFalse(panel.dirty)
        self.assertEqual(note.read_text(), '# Nueva nota\nTexto editado.')
        panel.close_note(); self.window.open_note(note)
        self.assertIn('Texto editado', self.window.panels[note].reader.toPlainText())

    def test_conflict_keeps_editor_buffer_and_external_file(self):
        note = self.root / 'Bienvenida/Nota.md'
        self.window.open_note(note, edit=True); panel = self.window.panels[note]
        panel.editor.setPlainText('Mi edición')
        note.write_text('Edición externa')
        self.assertFalse(panel.save())
        self.assertEqual(note.read_text(), 'Edición externa')
        self.assertEqual(panel.editor.toPlainText(), 'Mi edición')
        self.assertTrue(panel.dirty)

    def test_note_geometry_and_editing_survive_minimize_and_project_switch(self):
        note = self.root / 'Bienvenida/Nota.md'
        self.window.navigate(note.parent); self.window.open_note(note, edit=True)
        panel = self.window.panels[note]; panel.editor.setPlainText('Borrador')
        geometry = panel.geometry()
        panel.minimize(); self.window.navigate(self.root / 'Cuaderno'); self.window.navigate(note.parent)
        self.assertFalse(panel.isVisible()); panel.restore()
        self.assertEqual(panel.geometry(), geometry)
        self.assertEqual(panel.editor.toPlainText(), 'Borrador')
        self.assertIs(panel.pages.currentWidget(), panel.editor)
        self.window.resize(900, 650); self.app.processEvents()
        self.assertTrue(self.window.surface.rect().contains(panel.geometry()))

    def test_new_note_dialog_and_explorer_navigation(self):
        with patch('prosperus.shell.QInputDialog.getText', return_value=('Idea nueva', True)):
            self.window.new_note(folder=self.root / 'Cuaderno')
        note = self.root / 'Cuaderno/Idea nueva.md'
        self.assertTrue(note.exists())
        panel = self.window.panels[note]
        self.assertIs(panel.pages.currentWidget(), panel.editor)
        explorer = Explorer(self.window); explorer.go(self.root / 'Laboratorio')
        explorer.search.setText('hipotesis')
        self.assertEqual(explorer.items.count(), 1)
        explorer.activate(explorer.items.item(0))
        self.assertIn(self.root / 'Laboratorio/Apuntes/Hipótesis.md', self.window.panels)
        explorer.deleteLater()

    def test_body_search_in_map_explorer_and_project_drawer(self):
        project = self.root / 'Cursos 3D'
        note = project / '02 - Recursos y taller/Conceptos/Preparación.md'
        note.parent.mkdir(parents=True)
        note.write_text('# Preparación\n\nComprueba la calibración de la impresora.')
        self.window.refresh_projects(); self.window.navigate(project)
        self.window.search.setText('impresora')
        self.assertEqual([node.path for node in self.window.surface.nodes], [note])
        explorer = Explorer(self.window)
        explorer.search.setText('CALIBRACION')
        self.assertEqual(explorer.items.count(), 1)
        self.assertEqual(explorer.items.item(0).data(Qt.ItemDataRole.UserRole), note)
        explorer.reject(); explorer.deleteLater()
        self.window.drawer.reveal(); self.window.drawer.search.setText('impresora')
        self.assertEqual(self.window.drawer.filtered, [project])
        self.window.drawer.open_current()
        self.assertEqual(self.window.folder, project)

    def test_favorite_application_storage_and_accent_insensitive_filter(self):
        settings = QSettings(str(Path(self.temp.name) / 'settings.ini'), QSettings.Format.IniFormat)
        service = ApplicationService(settings=settings)
        app = {'id': 'org.test.Calculator.desktop', 'name': 'Cálculo', 'description': 'Calculadora', 'keywords': []}
        service.catalogue = [app]
        self.window.apps = service
        browser = ApplicationBrowser(self.window)
        browser.search.setText('calculo')
        self.assertEqual(browser.list.count(), 1)
        browser.toggle_favorite()
        self.assertEqual(ApplicationService(settings=settings).favorites, [{'id': app['id'], 'name': app['name']}])
        browser.toggle_favorite(); self.assertEqual(service.favorites, [])
        with patch.object(service, 'run') as run:
            browser.launch()
        run.assert_called_once_with('launch', app['id'])
        browser.reject(); browser.deleteLater()


if __name__ == '__main__':
    unittest.main()
