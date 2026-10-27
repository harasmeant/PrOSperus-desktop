"""Host-side tests; no installed GUI application is opened."""
import contextlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('applications', Path(__file__).with_name('applications.py'))
applications = importlib.util.module_from_spec(spec)
spec.loader.exec_module(applications)


class ApplicationsTest(unittest.TestCase):
    def setUp(self):
        self.app = Mock()
        self.app.get_id.return_value = 'test.desktop'
        self.app.should_show.return_value = True
        self.app.launch.return_value = True
        self.patch = patch.object(applications.Gio.AppInfo, 'get_all', return_value=[self.app])
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_exact_id_and_no_shell(self):
        applications.launch('test.desktop')
        self.app.launch.assert_called_once_with([], None)

    def test_unknown_and_hidden_are_rejected(self):
        with self.assertRaises(ValueError):
            applications.launch('$(not-an-app).desktop')
        self.app.should_show.return_value = False
        with self.assertRaises(ValueError):
            applications.launch('test.desktop')
        self.app.launch.assert_not_called()

    def test_failed_launch_reports_error(self):
        self.app.launch.return_value = False
        with self.assertRaises(RuntimeError):
            applications.launch('test.desktop')

    def test_gui_output_does_not_enter_json_pipe(self):
        def noisy_launch(*_):
            os.write(1, b'GUI output\n')
            os.write(2, b'GUI diagnostic\n')
            return True
        self.app.launch.side_effect = noisy_launch
        originals = [os.dup(1), os.dup(2)]
        with tempfile.TemporaryFile() as capture:
            try:
                for descriptor in (1, 2):
                    os.dup2(capture.fileno(), descriptor)
                applications.launch('test.desktop')
                os.write(1, b'{}\n')
            finally:
                for descriptor, original in zip((1, 2), originals):
                    os.dup2(original, descriptor)
                    os.close(original)
            capture.seek(0)
            self.assertEqual(capture.read(), b'{}\n')


if __name__ == '__main__':
    unittest.main()
