# SPDX-License-Identifier: GPL-3.0-only
from contextlib import redirect_stderr
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from prosperus.bootstrap import dependency_diagnostic, main


class BootstrapTests(unittest.TestCase):
    def test_missing_dependency_reports_live_space_without_installing_anything(self):
        with patch('prosperus.bootstrap.live_session', return_value=True), \
             patch('prosperus.bootstrap.shutil.disk_usage', return_value=SimpleNamespace(free=183 * 1024 * 1024)), \
             patch('prosperus.bootstrap.importlib.import_module', side_effect=ModuleNotFoundError('No module named PySide6')):
            output = io.StringIO()
            with redirect_stderr(output):
                self.assertEqual(main(), 1)
        message = output.getvalue()
        self.assertIn('183 MiB', message)
        self.assertIn('Fedora Live', message)
        self.assertIn('ModuleNotFoundError', message)
        self.assertIn('no se completó', message)
        self.assertIn('df -h', message)

    def test_broken_library_preserves_original_error_without_claiming_live(self):
        with patch('prosperus.bootstrap.live_session', return_value=False), \
             patch('prosperus.bootstrap.shutil.disk_usage', side_effect=OSError()):
            message = dependency_diagnostic(ImportError('libQt6Widgets.so: cannot open shared object file'))
        self.assertIn('libQt6Widgets.so', message)
        self.assertNotIn('Estás en Fedora Live', message)


if __name__ == '__main__':
    unittest.main()
