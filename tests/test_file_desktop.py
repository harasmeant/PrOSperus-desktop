# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QEvent, QMimeData, QPointF, QUrl, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent, QCloseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from prosperus.controls import SessionControls
from prosperus.file_actions import local_paths
from prosperus.shell import Desktop, Explorer


class FileDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'projects'; self.root.mkdir()
        self.project = self.root / 'Proyecto'; self.project.mkdir()
        self.note = self.project / 'Idea.md'; self.note.write_text('# Idea')
        (self.project / 'Carpeta').mkdir()
        self.window = Desktop(self.root)
        self.window.show(); self.window.activateWindow(); self.app.processEvents()
        self.window.navigate(self.project)

    def wait_copy(self):
        for _ in range(300):
            self.app.processEvents()
            if not self.window.files.busy:
                return
            QTest.qWait(10)
        self.fail('Copy worker did not finish')

    def tearDown(self):
        self.wait_copy()
        for panel in self.window.panels.values():
            panel.editor.setPlainText(panel.original)
        self.window.close(); self.window.deleteLater()
        QApplication.clipboard().clear(); self.app.processEvents()

    def test_new_project_is_always_at_root_and_appears_in_drawer(self):
        with patch('prosperus.shell.QInputDialog.getText', return_value=('Mi proyecto', True)):
            self.window.new_project()
        self.assertEqual(self.window.folder, self.root / 'Mi proyecto')
        self.assertIn(self.root / 'Mi proyecto', self.window.project_paths)
        self.assertFalse((self.project / 'Mi proyecto').exists())
        self.window.drawer.reveal()
        self.assertIn(self.root / 'Mi proyecto', self.window.drawer.filtered)

    def test_map_select_copy_paste_and_double_click(self):
        node = next(n for n in self.window.surface.nodes if n.path == self.note)
        QTest.mouseClick(node, Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.surface.selection, [self.note])
        self.assertFalse(self.window.panels)
        QTest.keyClick(node, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(local_paths(QApplication.clipboard().mimeData()), [self.note])
        self.window.navigate(self.project / 'Carpeta')
        QTest.keyClick(self.window.surface, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        self.wait_copy()
        copied = self.project / 'Carpeta/Idea.md'
        self.assertEqual(copied.read_text(), self.note.read_text())
        node = self.window.surface.nodes[0]
        QTest.mouseDClick(node, Qt.MouseButton.LeftButton)
        self.assertIn(copied, self.window.panels)

    def test_multiselection_duplicate_and_enter(self):
        for node in self.window.surface.nodes:
            QTest.mouseClick(node, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(len(self.window.surface.selection), 2)
        self.window.surface.setFocus()
        QTest.keyClick(self.window.surface, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        self.wait_copy()
        self.assertTrue((self.project / 'Idea - copia.md').exists())
        self.assertTrue((self.project / 'Carpeta - copia').is_dir())
        node = next(n for n in self.window.surface.nodes if n.path == self.note)
        QTest.keyClick(node, Qt.Key.Key_Return)
        self.assertIn(self.note, self.window.panels)

    def test_editor_clipboard_and_ctrl_w_target_focused_note(self):
        self.window.open_note(self.note, edit=True)
        panel = self.window.panels[self.note]
        panel.editor.selectAll()
        QTest.keyClick(panel.editor, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(QApplication.clipboard().text(), '# Idea')
        QApplication.clipboard().setText('Edited text')
        QTest.keyClick(panel.editor, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(panel.editor.toPlainText(), 'Edited text')
        panel.editor.setPlainText(panel.original)
        other = self.project / 'Otra.md'; other.write_text('Otra')
        self.window.open_note(other)
        panel.editor.setFocus(); self.app.processEvents()
        QTest.keyClick(panel.editor, Qt.Key.Key_W, Qt.KeyboardModifier.ControlModifier)
        self.assertNotIn(self.note, self.window.panels)
        self.assertIn(other, self.window.panels)

    def test_explorer_clipboard_and_backspace_use_its_own_folder(self):
        explorer = Explorer(self.window); explorer.show(); explorer.activateWindow()
        explorer.go(self.project); explorer.items.setCurrentRow(1); explorer.items.setFocus()
        self.app.processEvents()
        QTest.keyClick(explorer.items, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(local_paths(QApplication.clipboard().mimeData()), [self.note])
        explorer.go(self.project / 'Carpeta'); explorer.items.setFocus()
        QTest.keyClick(explorer.items, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
        self.wait_copy()
        self.assertEqual(explorer.items.count(), 1)
        QTest.keyClick(explorer.items, Qt.Key.Key_Backspace)
        self.assertEqual(explorer.folder, self.project)
        self.assertEqual(self.window.folder, self.project)
        explorer.reject(); explorer.deleteLater()

    def test_external_clipboard_import_and_remote_rejection(self):
        source = Path(self.temp.name) / 'Desde archivos.md'; source.write_text('Imported')
        mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(str(source))])
        QApplication.clipboard().setMimeData(mime)
        self.window.files.paste(self.project); self.wait_copy()
        self.assertEqual((self.project / source.name).read_text(), 'Imported')
        self.assertTrue(source.exists())
        mime = QMimeData(); mime.setUrls([QUrl('https://example.com/not-a-file')])
        with self.assertRaises(ValueError):
            local_paths(mime)

    def test_drop_on_folder_copies_into_that_folder_without_moving_source(self):
        mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(str(self.note))])
        node = next(n for n in self.window.surface.nodes if n.path.is_dir())
        position = node.geometry().center()
        enter = QDragEnterEvent(position, Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                                mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.window.surface.dragEnterEvent(enter)
        event = QDropEvent(QPointF(position), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                           mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.window.surface.dropEvent(event); self.wait_copy()
        self.assertTrue(event.isAccepted())
        self.assertEqual(event.dropAction(), Qt.DropAction.CopyAction)
        self.assertEqual((self.project / 'Carpeta/Idea.md').read_text(), '# Idea')
        self.assertTrue(self.note.exists())

    def test_failed_worker_reports_error_and_can_copy_again(self):
        link = Path(self.temp.name) / 'Link.md'; link.symlink_to(self.note)
        self.window.files.transfer([link], self.project); self.wait_copy()
        self.assertIn('No se ha completado', self.window.status.text())
        self.assertFalse((self.project / 'Link.md').exists())
        self.window.files.transfer([self.note], self.project); self.wait_copy()
        self.assertEqual((self.project / 'Idea - copia.md').read_text(), '# Idea')

    def test_super_alone_toggles_but_combinations_do_not(self):
        target = self.window.surface
        with patch.object(self.window, 'toggle_applications') as toggle:
            for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
                self.window.keys.eventFilter(target, QKeyEvent(kind, Qt.Key.Key_Meta, Qt.KeyboardModifier.NoModifier))
            self.app.processEvents(); toggle.assert_called_once()
            toggle.reset_mock()
            self.window.keys.eventFilter(target, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Meta, Qt.KeyboardModifier.NoModifier))
            self.window.keys.eventFilter(target, QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key.Key_E, Qt.KeyboardModifier.MetaModifier))
            self.window.keys.eventFilter(target, QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Meta, Qt.KeyboardModifier.NoModifier))
            self.app.processEvents(); toggle.assert_not_called()

    def test_application_fallback_toggle_and_navigation_history(self):
        self.window.apps.catalogue = [{'id': 'test.desktop', 'name': 'Test', 'description': '', 'keywords': []}]
        self.window.surface.setFocus()
        QTest.keyClick(self.window.surface, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertIsNotNone(self.window.app_browser)
        browser = self.window.app_browser
        QTest.keyClick(browser.search, Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents(); self.assertIsNone(self.window.app_browser)
        self.window.navigate(self.project / 'Carpeta'); self.window.history_step(-1)
        self.assertEqual(self.window.folder, self.project)
        self.window.history_step(1); self.assertEqual(self.window.folder, self.project / 'Carpeta')

    def test_copy_blocks_close_and_power_until_finished(self):
        self.window.files.thread = object()
        event = QCloseEvent(); self.window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.window.system_session = True
        with patch('prosperus.shell.subprocess.run') as run:
            self.window.power('poweroff')
        run.assert_not_called()
        self.window.files.thread = None

    def test_hardware_keys_only_dispatch_in_own_session(self):
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_VolumeUp, Qt.KeyboardModifier.NoModifier)
        with patch.object(self.window.controls, 'handle_key', return_value=True) as handle:
            self.window.keys.eventFilter(self.window.surface, event)
            handle.assert_not_called()
            self.window.system_session = True
            self.assertTrue(self.window.keys.eventFilter(self.window.surface, event))
            handle.assert_called_once_with(Qt.Key.Key_VolumeUp)

    def test_controls_use_argument_arrays_and_disable_missing_capabilities(self):
        controls = SessionControls()
        process = MagicMock(); process.state.return_value = controls.process.ProcessState.NotRunning
        controls.process = process
        with patch.object(controls, 'available', return_value=True):
            controls.execute('volume-up')
        process.start.assert_called_once_with('wpctl', ['set-volume', '@DEFAULT_AUDIO_SINK@', '5%+', '--limit', '1.0'])
        with patch('prosperus.controls.shutil.which', return_value=None):
            self.assertFalse(controls.available('volume-up'))
        with patch('prosperus.controls.shutil.which', return_value='/usr/bin/brightnessctl'), patch('prosperus.controls.Path.glob', return_value=iter([])):
            self.assertFalse(controls.available('brightness-up'))


if __name__ == '__main__':
    unittest.main()
