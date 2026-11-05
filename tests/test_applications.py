"""Verify the GIO boundary without opening any installed application."""
# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import tempfile
import unittest
from unittest.mock import Mock, patch

from prosperus import applications


class ApplicationsTests(unittest.TestCase):
    def setUp(self):
        self.app = Mock()
        self.app.get_id.return_value = 'test.desktop'
        self.app.should_show.return_value = True
        self.app.launch.return_value = True
        self.patch = patch.object(applications.Gio.AppInfo, 'get_all', return_value=[self.app])
        self.patch.start(); self.addCleanup(self.patch.stop)

    def test_exact_id_without_shell(self):
        applications.launch('test.desktop')
        self.app.launch.assert_called_once_with([], None)

    def test_unknown_and_hidden_rejected(self):
        with self.assertRaises(ValueError):
            applications.launch('$(not-an-app).desktop')
        self.app.should_show.return_value = False
        with self.assertRaises(ValueError):
            applications.launch('test.desktop')
        self.app.launch.assert_not_called()

    def test_failed_launch_reported(self):
        self.app.launch.return_value = False
        with self.assertRaises(RuntimeError):
            applications.launch('test.desktop')

    def test_app_output_does_not_corrupt_json_response(self):
        def noisy_launch(*_):
            os.write(1, b'GUI output\n'); os.write(2, b'GUI diagnostic\n')
            return True
        self.app.launch.side_effect = noisy_launch
        originals = [os.dup(1), os.dup(2)]
        with tempfile.TemporaryFile() as capture:
            try:
                for descriptor in (1, 2):
                    os.dup2(capture.fileno(), descriptor)
                applications.launch('test.desktop'); os.write(1, b'{}\n')
            finally:
                for descriptor, original in zip((1, 2), originals):
                    os.dup2(original, descriptor); os.close(original)
            capture.seek(0)
            self.assertEqual(capture.read(), b'{}\n')


class LauncherGridTests(unittest.TestCase):
    def test_app_item_icons_text_and_tooltip(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from prosperus.appearance import Palette
        from prosperus.launcher import app_item

        app = QApplication.instance() or QApplication([])
        colors = Palette(120)

        item = app_item({'id': 'a.desktop', 'name': 'Editor', 'description': '', 'icon': 'no-such-icon-xyz'}, set(), colors)
        self.assertEqual(item.text(), 'Editor')
        self.assertEqual(item.toolTip(), 'Editor')
        self.assertFalse(item.icon().isNull())

        item = app_item({'id': 'a.desktop', 'name': 'Editor', 'description': 'Texto', 'icon': '/no/such/file.png'}, {'a.desktop'}, colors)
        self.assertTrue(item.text().startswith('★'))
        self.assertEqual(item.toolTip(), 'Texto')
        self.assertFalse(item.icon().isNull())
        self.assertEqual(item.data(Qt.ItemDataRole.UserRole)['kind'], 'app')

    def test_sway_keeps_desktop_dialogs_floating(self):
        from pathlib import Path
        config = (Path(__file__).parents[1] / 'image/rootfs/etc/sway/prosperus.conf').read_text(encoding='utf-8')
        # La regla que fija el escritorio no debe alcanzar a sus diálogos (mismo app_id).
        self.assertNotIn('for_window [app_id="org.prosperus.Desktop"] border none, floating disable', config)
        self.assertIn('title="^PrOSperus desktop$"] border none, floating disable', config)
