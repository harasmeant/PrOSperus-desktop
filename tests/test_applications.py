"""Verify the GIO boundary without opening any installed application."""
# SPDX-License-Identifier: GPL-3.0-only
import os
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
