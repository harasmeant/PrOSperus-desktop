# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prosperus.model import Vault


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'vault'
        self.root.mkdir()
        (self.root / 'Proyecto/Apuntes').mkdir(parents=True)
        (self.root / 'Proyecto/Inicio.md').write_text('# Inicio\n[[Apuntes/Árbol|Idea]]\n`[[literal]]`\n')
        (self.root / 'Proyecto/Apuntes/Árbol.md').write_text('# Árbol\nUn texto.')
        self.vault = Vault(self.root)

    def test_recursive_accent_insensitive_search(self):
        # The linked note matches by name; Inicio matches the wikilink in its text.
        self.assertEqual([p.name for p in self.vault.search('ARBOL')], ['Árbol.md', 'Inicio.md'])

    def test_search_combines_path_and_body_terms_and_respects_folder_scope(self):
        note = self.root / 'Proyecto/Apuntes/Árbol.md'
        note.write_text('# Investigación\n\nLa fotosíntesis transforma energía.')
        (self.root / 'Otro').mkdir()
        (self.root / 'Otro/Documento.md').write_text('Fotosíntesis')
        self.assertEqual(self.vault.search('APUNTES fotosintesis energia'), [note])
        self.assertEqual(self.vault.search('fotosintesis', self.root / 'Proyecto'), [note])
        self.assertEqual(self.vault.search('fotosintesis inexistente'), [])
        self.assertEqual(self.vault.search_projects('energia'), [self.root / 'Proyecto'])
        self.assertEqual(self.vault.search_projects('otro'), [self.root / 'Otro'])

    def test_search_reads_current_saved_content_and_skips_unreadable_notes(self):
        note = self.root / 'Proyecto/Apuntes/Árbol.md'
        note.write_text('Constelación')
        self.assertEqual(self.vault.search('constelacion'), [note])
        note.write_text('Nebulosa')
        self.assertEqual(self.vault.search('constelacion'), [])
        broken = self.root / 'Broken.md'; broken.write_bytes(b'\xff\xfe')
        huge = self.root / 'Huge.md'; huge.write_bytes(b'x' * (Vault.MAX_NOTE_BYTES + 1))
        self.assertEqual(self.vault.search('nebulosa'), [note])
        self.assertEqual(self.vault.search('broken'), [broken])
        self.assertEqual(self.vault.search('huge'), [huge])
        original = self.vault.read
        def limited(path):
            if path.name == 'Inicio.md':
                raise PermissionError('Unreadable')
            return original(path)
        with patch.object(self.vault, 'read', side_effect=limited):
            self.assertEqual(self.vault.search('nebulosa'), [note])

    def test_content_search_does_not_read_hidden_or_external_files(self):
        outside = Path(self.temp.name) / 'outside.md'; outside.write_text('confidencial')
        (self.root / 'Enlace.md').symlink_to(outside)
        (self.root / '.oculta.md').write_text('confidencial')
        (self.root / 'Documento.txt').write_text('confidencial')
        self.assertEqual(self.vault.search('confidencial'), [])

    def test_links_and_read_only(self):
        source = self.root / 'Proyecto/Inicio.md'
        before = source.read_bytes()
        rendered = self.vault.markdown(source)
        self.assertIn('[Idea](Apuntes/%C3%81rbol)', rendered)
        self.assertIn('`[[literal]]`', rendered)
        self.assertEqual(self.vault.resolve_note('Apuntes/%C3%81rbol', source).name, 'Árbol.md')
        self.assertEqual(before, source.read_bytes())

    def test_external_and_traversal_links_rejected(self):
        outside = Path(self.temp.name) / 'outside.md'
        outside.write_text('private')
        source = self.root / 'Proyecto/Inicio.md'
        for target in ('https://example.org', 'file://' + str(outside), '../../outside.md'):
            with self.assertRaises(ValueError):
                self.vault.resolve_note(target, source)

    def test_symlink_escape_and_hidden_files_not_indexed(self):
        outside = Path(self.temp.name) / 'external'
        outside.mkdir()
        (outside / 'Secret.md').write_text('private')
        (self.root / 'Outside').symlink_to(outside)
        (self.root / '.hidden').mkdir()
        (self.root / '.hidden/Hidden.md').write_text('hidden')
        names = [p.name for p in self.vault.notes()]
        self.assertNotIn('Secret.md', names)
        self.assertNotIn('Hidden.md', names)

    def test_ambiguous_names_and_missing_targets(self):
        (self.root / 'Other').mkdir()
        (self.root / 'Other/Árbol.md').write_text('duplicate')
        source = self.root / 'Proyecto/Inicio.md'
        with self.assertRaises(ValueError):
            self.vault.resolve_note('Árbol', source)
        with self.assertRaises(FileNotFoundError):
            self.vault.resolve_note('Missing', source)

    def test_large_notes_rejected(self):
        note = self.root / 'Large.md'
        note.write_bytes(b'x' * (Vault.MAX_NOTE_BYTES + 1))
        with self.assertRaises(ValueError):
            self.vault.read(note)

    def test_create_and_save_note_without_overwriting_existing_files(self):
        folder = self.vault.create_folder(self.root, 'Nuevo proyecto')
        note = self.vault.create_note(folder, 'Primera idea')
        self.assertEqual(note.name, 'Primera idea.md')
        initial = self.vault.read(note)
        self.vault.save_note(note, '# Idea\n\nTexto con acentos: árbol.', initial)
        self.assertIn('árbol', self.vault.read(note))
        with self.assertRaises(FileExistsError):
            self.vault.create_note(folder, 'Primera idea')
        self.assertIn('árbol', self.vault.read(note))

    def test_external_modifications_preserved_on_save_conflict(self):
        note = self.root / 'Proyecto/Inicio.md'
        initial = self.vault.read(note)
        note.write_text('Cambio externo')
        with self.assertRaises(ValueError):
            self.vault.save_note(note, 'Cambio de la ventana', initial)
        self.assertEqual(note.read_text(), 'Cambio externo')
        self.assertFalse(list(note.parent.glob('.prosperus-*')))

    def test_invalid_names_and_symlink_destinations_rejected(self):
        for name in ('', '   ', '../fuera', '.oculta', 'a/b', 'a\\b', 'a\0b', 'a\nb'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.vault.create_note(self.root, name)
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.root / 'Escape').symlink_to(outside)
        with self.assertRaises(ValueError):
            self.vault.create_note(self.root / 'Escape', 'No escribir')
        self.assertEqual(list(outside.iterdir()), [])

    def test_save_preserves_permissions_and_rejects_large_changes(self):
        note = self.root / 'Proyecto/Inicio.md'
        note.chmod(0o640)
        original = self.vault.read(note)
        with self.assertRaises(ValueError):
            self.vault.save_note(note, 'x' * (Vault.MAX_NOTE_BYTES + 1), original)
        self.assertEqual(self.vault.read(note), original)
        self.vault.save_note(note, 'Guardado', original)
        self.assertEqual(note.stat().st_mode & 0o777, 0o640)


if __name__ == '__main__':
    unittest.main()
