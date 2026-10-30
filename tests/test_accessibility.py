# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAccessible
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from prosperus.accessibility import Accessibility, AccessibilityDialog
from prosperus.controls import ControlsDialog
from prosperus.hardware import HardwareDialog, pci_devices
from prosperus.shell import Desktop, Explorer


class AccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'Proyecto'; self.project.mkdir()
        self.note = self.project / 'Idea.md'; self.note.write_text('# Idea')
        self.settings = QSettings(str(self.root / 'preferences.ini'), QSettings.Format.IniFormat)
        self.window = Desktop(self.root, settings=self.settings)
        self.window.show(); self.window.activateWindow(); self.window.navigate(self.project)
        self.app.processEvents()

    def tearDown(self):
        for panel in self.window.panels.values():
            panel.editor.setPlainText(panel.original)
        self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def test_preferences_persist_and_invalid_scale_falls_back(self):
        options = Accessibility(150, True, True, True)
        self.assertTrue(options.save(self.settings))
        reopened = QSettings(self.settings.fileName(), QSettings.Format.IniFormat)
        self.assertEqual(Accessibility.load(reopened), options)
        reopened.setValue('accessibility/text_scale', 'not a number')
        self.assertEqual(Accessibility.load(reopened).text_scale, 100)

    def test_applying_preferences_preserves_unsaved_note_and_navigation(self):
        self.window.open_note(self.note, edit=True)
        panel = self.window.panels[self.note]
        panel.editor.setPlainText('texto sin guardar')
        dialog = AccessibilityDialog(self.window)
        dialog.scale.setCurrentIndex(2); dialog.large.setChecked(True); dialog.contrast.setChecked(True)
        dialog.apply(); self.app.processEvents()
        self.assertEqual(panel.editor.toPlainText(), 'texto sin guardar')
        self.assertEqual(self.note.read_text(), '# Idea')
        self.assertEqual(self.window.folder, self.project)
        self.assertEqual(self.window.colors.text, '#ffffff')
        self.assertEqual(panel.colors.base, '#000000')
        self.assertIsNone(self.window.background.wallpaper)
        self.assertGreaterEqual(self.window.dock_scroll.height(), 80)
        self.assertIn('font-size: 20px', self.window.styleSheet())
        self.window.navigate(self.root)
        self.assertEqual(self.window.colors.text, '#ffffff')
        dialog.reject(); dialog.deleteLater()

    def test_single_click_is_optional_and_control_click_keeps_selection(self):
        node = self.window.surface.nodes[0]
        QTest.mouseClick(node, Qt.MouseButton.LeftButton)
        self.assertFalse(self.window.panels)
        self.window.accessibility = Accessibility(single_click=True)
        QTest.mouseClick(node, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
        self.assertFalse(self.window.panels)
        QTest.mouseClick(node, Qt.MouseButton.LeftButton)
        self.assertIn(self.note, self.window.panels)

    def test_controls_expose_distinct_accessible_names_and_keyboard_activation(self):
        with patch.object(self.window.controls, 'available', return_value=True):
            dialog = ControlsDialog(self.window)
        dialog.show(); dialog.activateWindow(); self.app.processEvents()
        buttons = dialog.findChildren(QPushButton)
        names = [QAccessible.queryAccessibleInterface(b).text(QAccessible.Text.Name) for b in buttons]
        self.assertIn('Subir volumen', names); self.assertIn('Subir brillo', names)
        self.assertNotIn('+', names); self.assertNotIn('−', names)
        volume = buttons[names.index('Subir volumen')]
        volume.setFocus()
        with patch.object(self.window.controls, 'execute') as execute:
            QTest.keyClick(volume, Qt.Key.Key_Space)
            execute.assert_called_once_with('volume-up')
        QTest.keyClick(volume, Qt.Key.Key_Tab)
        self.assertIsNot(self.app.focusWidget(), volume)
        dialog.reject(); dialog.deleteLater()

    def test_search_shortcuts_and_note_switching_preserve_text_keys(self):
        self.window.surface.setFocus()
        QTest.keyClick(self.window.surface, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.assertIs(self.app.focusWidget(), self.window.search)
        self.window.open_note(self.note, edit=True)
        second = self.project / 'Otra.md'; second.write_text('# Otra')
        self.window.open_note(second, edit=True)
        panel = self.window.panels[second]
        QTest.keyClick(panel.editor, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
        self.assertIs(self.app.focusWidget(), self.window.panels[self.note].editor)
        editor = self.window.panels[self.note].editor
        editor.selectAll(); QTest.keyClicks(editor, 'primera linea')
        QTest.keyClick(editor, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(editor.toPlainText(), '# Idea')
        QTest.keyClick(editor, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(editor.toPlainText(), 'primera linea')
        QTest.keyClick(editor, Qt.Key.Key_Home, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.window.folder, self.project)
        self.assertEqual(editor.textCursor().position(), 0)

    def test_explorer_search_and_keyboard_context_menu(self):
        dialog = Explorer(self.window); dialog.show(); dialog.activateWindow(); self.app.processEvents()
        dialog.items.setFocus(); dialog.items.setCurrentRow(0)
        with patch.object(dialog, 'context_menu') as menu:
            QTest.keyClick(dialog.items, Qt.Key.Key_F10, Qt.KeyboardModifier.ShiftModifier)
            menu.assert_called_once()
        QTest.keyClick(dialog.items, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.assertIs(self.app.focusWidget(), dialog.search)
        dialog.reject(); dialog.deleteLater()

    def test_hardware_reports_unavailable_inventory(self):
        with patch('prosperus.hardware.pci_devices', side_effect=OSError('no disponible')):
            dialog = HardwareDialog(self.window)
        self.assertIn('No se pudo consultar', dialog.status.text())
        self.assertEqual(dialog.devices.topLevelItemCount(), 0)
        dialog.reject(); dialog.deleteLater()


class HardwareTests(unittest.TestCase):
    def test_vendor_driver_and_unbound_device_without_system_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); pci = root / 'devices'; pci.mkdir()
            driver = root / 'nvidia'; driver.mkdir()
            for name, vendor in [('01', '0x10de'), ('02', '0x8086'), ('03', '0x1002')]:
                device = pci / name; device.mkdir()
                (device / 'class').write_text('0x030000')
                (device / 'vendor').write_text(vendor); (device / 'device').write_text('0x1234')
            (pci / '01/driver').symlink_to(driver, target_is_directory=True)
            rows = pci_devices(pci)
            self.assertIn('NVIDIA', rows[0][0]); self.assertEqual(rows[0][1], 'nvidia')
            self.assertIn('Intel', rows[1][0]); self.assertIn('AMD', rows[2][0])
            self.assertEqual(rows[1][2], 'Sin controlador asociado')
            self.assertEqual(rows[0][2], 'Controlador asociado')
