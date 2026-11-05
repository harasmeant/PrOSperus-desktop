# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import tempfile
import time
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QWidget

from prosperus.incoming import Incoming


class IncomingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def pump(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            QCoreApplication.processEvents(); time.sleep(0.05)

    def test_finished_download_goes_to_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); project = tmp / 'Lab'; project.mkdir()
            parent = QWidget()
            incoming = Incoming(parent, lambda: project, tmp / 'entrantes')
            incoming.timer.setInterval(100)
            (tmp / 'entrantes' / 'informe.pdf.part').write_bytes(b'medio')
            self.pump(0.6)
            self.assertFalse((project / 'Documentos').exists())
            (tmp / 'entrantes' / 'informe.pdf.part').rename(tmp / 'entrantes' / 'informe.pdf')
            self.pump(1.0)
            self.assertTrue((project / 'Documentos' / 'informe.pdf').exists())
            self.assertFalse((tmp / 'entrantes' / 'informe.pdf').exists())

    def test_without_project_file_waits(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            incoming = Incoming(QWidget(), lambda: None, tmp / 'entrantes')
            incoming.timer.setInterval(100); messages = []
            incoming.message.connect(messages.append)
            (tmp / 'entrantes' / 'foto.png').write_bytes(b'x')
            self.pump(0.8)
            self.assertTrue((tmp / 'entrantes' / 'foto.png').exists())
            self.assertTrue(any('Abre un proyecto' in m for m in messages))


if __name__ == '__main__':
    unittest.main()
