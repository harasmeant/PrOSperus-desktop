# SPDX-License-Identifier: GPL-3.0-only
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prosperus.model import Vault
from prosperus.transfers import copy_into, copy_to_handle


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'projects'; self.root.mkdir()
        self.vault = Vault(self.root)
        self.external = Path(self.temp.name) / 'Trabajo'; self.external.mkdir()
        (self.external / 'Nota.md').write_text('# Idea\n[[Otra]]')
        (self.external / 'Subcarpeta').mkdir()
        (self.external / 'Subcarpeta/Otra.md').write_text('Contenido')
        (self.external / 'wallpaper.png').write_bytes(b'attachment')
        (self.external / '.metadata').write_text('metadata')

    def test_import_tree_preserves_sources_attachments_and_relative_links(self):
        result = copy_into(self.vault, [self.external, self.external / 'Nota.md'], self.root)
        self.assertEqual(result, [self.root / 'Trabajo'])
        before = {p.relative_to(self.external): p.read_bytes() for p in self.external.rglob('*') if p.is_file()}
        after = {p.relative_to(result[0]): p.read_bytes() for p in result[0].rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual((result[0] / 'Nota.md').read_text(), '# Idea\n[[Otra]]')

    def test_collision_names_and_permissions(self):
        source = self.external / 'Nota.md'; source.chmod(0o640)
        paths = [copy_into(self.vault, [source], self.root)[0] for _ in range(3)]
        self.assertEqual([p.name for p in paths], ['Nota.md', 'Nota - copia.md', 'Nota - copia 2.md'])
        self.assertEqual(paths[1].stat().st_mode & 0o777, 0o640)
        copy_into(self.vault, [self.external], self.root)
        self.assertEqual(copy_into(self.vault, [self.external], self.root), [self.root / 'Trabajo - copia'])
        self.assertEqual(source.read_text(), '# Idea\n[[Otra]]')

    def test_failure_rolls_back_whole_batch_without_touching_existing(self):
        existing = self.root / 'Nota.md'; existing.write_text('Existing content')
        def fail_second(source, target):
            if source.name == 'Otra.md':
                target.write(b'partial')
                raise OSError('Disco lleno')
            return copy_to_handle(source, target)
        with patch('prosperus.transfers.copy_to_handle', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'Disco lleno'):
                copy_into(self.vault, [self.external / 'Nota.md', self.external / 'Subcarpeta'], self.root)
        self.assertEqual(list(self.root.iterdir()), [existing])
        self.assertEqual(existing.read_text(), 'Existing content')
        self.assertEqual((self.external / 'Subcarpeta/Otra.md').read_text(), 'Contenido')

    def test_symlink_fifo_and_recursive_destination_rejected(self):
        link = self.external / 'Enlace.md'; link.symlink_to(self.external / 'Nota.md')
        with self.assertRaises(ValueError):
            copy_into(self.vault, [self.external], self.root)
        link.unlink()
        fifo = self.external / 'pipe'; os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            copy_into(self.vault, [fifo], self.root)
        fifo.unlink()
        project = copy_into(self.vault, [self.external], self.root)[0]
        with self.assertRaisesRegex(ValueError, 'dentro de sí misma'):
            copy_into(self.vault, [project], project / 'Subcarpeta')
        with self.assertRaises(ValueError):
            copy_into(self.vault, [project], self.external)

    def test_exclusive_creation_does_not_remove_racing_file(self):
        target = self.root / 'Nota.md'
        def occupied(*args):
            target.write_text('Created by another program')
            return target
        with patch('prosperus.transfers.available_name', side_effect=occupied):
            with self.assertRaises(FileExistsError):
                copy_into(self.vault, [self.external / 'Nota.md'], self.root)
        self.assertEqual(target.read_text(), 'Created by another program')


if __name__ == '__main__':
    unittest.main()
