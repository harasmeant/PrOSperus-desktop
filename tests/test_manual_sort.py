# SPDX-License-Identifier: GPL-3.0-only
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget

from prosperus import file_routing as r
from prosperus.incoming import SortDialog, move_files


class ManualSortTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / 'Lab'
        self.project.mkdir()
        for name in ('Plan.md', 'foto.png', 'informe.PDF', 'pieza.stl', 'wallpaper.png', '.oculto'):
            (self.project / name).write_bytes(b'x')
        (self.project / 'Apuntes').mkdir(); (self.project / 'Imágenes').mkdir()
        (self.project / 'Apuntes' / 'dentro.png').write_bytes(b'x')
        os.environ['XDG_CONFIG_HOME'] = str(Path(self.tmp.name) / 'config')

    def tearDown(self):
        os.environ.pop('XDG_CONFIG_HOME', None); self.tmp.cleanup()

    def test_plan_defaults(self):
        plan = {p.name: (d, c) for p, d, c in r.sort_plan(self.project, {})}
        self.assertEqual(plan, {'Apuntes': (None, False), 'foto.png': ('Imágenes', True),
                                'informe.PDF': ('Documentos', True), 'Plan.md': ('Documentos', False),
                                'pieza.stl': (None, False)})

    def test_dialog_moves_only_checked_and_never_subfolders(self):
        parent = QWidget(); dialog = SortDialog(parent, self.project)
        moved, errors = move_files(None, dialog.choices())
        self.assertEqual(errors, [])
        self.assertTrue((self.project / 'Imágenes' / 'foto.png').exists())
        self.assertTrue((self.project / 'Documentos' / 'informe.PDF').exists())
        for name in ('Plan.md', 'pieza.stl', 'wallpaper.png'):
            self.assertTrue((self.project / name).exists(), name)
        self.assertTrue((self.project / 'Apuntes' / 'dentro.png').exists())

    def test_new_destination_is_remembered(self):
        moved, _ = move_files(None, [(self.project / 'pieza.stl', 'Modelos 3D')])
        self.assertEqual(moved, [self.project / 'Modelos 3D' / 'pieza.stl'])
        self.assertEqual(r.load_memory(), {'stl': 'Modelos 3D'})

    def test_same_name_gets_number(self):
        (self.project / 'Imágenes' / 'foto.png').write_bytes(b'y')
        moved, _ = move_files(None, [(self.project / 'foto.png', 'Imágenes')])
        self.assertEqual(moved[0].name, 'foto (2).png')


if __name__ == '__main__':
    unittest.main()
