# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import tempfile
import unittest
from pathlib import Path

from prosperus import file_routing as r


class FileRoutingTest(unittest.TestCase):
    def test_extension(self):
        self.assertEqual(r.extension('Foto.JPG'), 'jpg')
        self.assertEqual(r.extension('copia.tar.gz'), 'tar.gz')
        self.assertEqual(r.extension('README'), '')
        self.assertEqual(r.extension('.bashrc'), '')

    def test_folder_for_known_and_remembered(self):
        self.assertEqual(r.folder_for('plano.pdf', {}), 'Documentos')
        self.assertEqual(r.folder_for('foto.webp', {}), 'Imágenes')
        self.assertEqual(r.folder_for('pieza.stl', {}), None)
        self.assertEqual(r.folder_for('pieza.STL', {'stl': 'Modelos 3D'}), 'Modelos 3D')
        # Lo recordado manda sobre lo conocido.
        self.assertEqual(r.folder_for('notas.txt', {'txt': 'Apuntes'}), 'Apuntes')

    def test_partial_downloads_wait(self):
        for name in ('video.mp4.part', 'x.crdownload', '.oculto', 'a.tmp'):
            self.assertTrue(r.is_partial(name), name)
        self.assertFalse(r.is_partial('video.mp4'))

    def test_route_creates_type_folder_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); project = tmp / 'Laboratorio'; project.mkdir(); inbox = tmp / 'in'; inbox.mkdir()
            self.assertFalse((project / 'Imágenes').exists())
            for _ in range(2):
                (inbox / 'Foto.png').write_bytes(b'x')
                target = r.route(inbox / 'Foto.png', project, {})
            self.assertEqual(target, project / 'Imágenes' / 'Foto (2).png')
            self.assertTrue((project / 'Imágenes' / 'Foto.png').exists())
            (inbox / 'a.tar.gz').write_bytes(b'x'); (inbox / 'b.tar.gz').write_bytes(b'x')
            r.route(inbox / 'a.tar.gz', project, {})
            (inbox / 'b.tar.gz').rename(inbox / 'a.tar.gz')
            self.assertEqual(r.route(inbox / 'a.tar.gz', project, {}).name, 'a (2).tar.gz')
            (inbox / 'pieza.stl').write_bytes(b'x')
            self.assertIsNone(r.route(inbox / 'pieza.stl', project, {}))
            self.assertTrue((inbox / 'pieza.stl').exists())

    def test_memory_round_trip_and_unsafe_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'destinos.json'
            self.assertEqual(r.load_memory(path), {})
            r.save_memory({'stl': 'Modelos 3D'}, path)
            self.assertEqual(r.load_memory(path), {'stl': 'Modelos 3D'})
            path.write_text('{"x": "../fuera", "y": ".oculta", "z": "Bien"}')
            self.assertEqual(r.load_memory(path), {'z': 'Bien'})

    def test_project_root(self):
        root = Path('/v')
        self.assertEqual(r.project_root(root, Path('/v/Lab/Apuntes')), Path('/v/Lab'))
        self.assertIsNone(r.project_root(root, root))

    def test_type_folders_lists_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Modelos 3D').mkdir(); (Path(tmp) / '.papelera').mkdir()
            names = r.type_folders(tmp)
            self.assertIn('Modelos 3D', names); self.assertIn('Documentos', names); self.assertNotIn('.papelera', names)


if __name__ == '__main__':
    unittest.main()
