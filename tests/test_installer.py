# SPDX-License-Identifier: GPL-3.0-only
"""Instalador de programas: aviso de qué se conserva al apagar."""
import unittest




class PersistenceNoteTests(unittest.TestCase):
    def test_note_depends_on_usb_persistence(self):
        import tempfile
        from pathlib import Path
        from prosperus.installer import persistence_note
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'persistente'
            self.assertIn('se perderá', persistence_note(marker))
            marker.touch()
            system = Path(tmp) / 'sistema'
            self.assertIn('Flathub se conservan', persistence_note(marker, system))
            system.touch()
            self.assertIn('de Fedora o de Flathub, se conserva', persistence_note(marker, system))
        script = (Path(__file__).parents[1] / 'image/rootfs/usr/libexec/prosperus-persistence').read_text(encoding='utf-8')
        self.assertIn('mount --bind "$data/flatpak" "$fp"', script)
        # La marca de persistencia se crea al final, cuando ya está todo montado.
        self.assertGreater(script.index('touch /run/prosperus-persistent'), script.index('"$data/flatpak" "$fp"'))


class RecommendedTests(unittest.TestCase):
    def test_catalog_is_consistent(self):
        from prosperus.recommended import recommended
        entries = recommended()
        ids = [e['id'] for e in entries]
        self.assertEqual(len(ids), len(set(ids)))
        for e in entries:
            self.assertIn(e['source'], ('fedora', 'flathub'))
            if e['source'] == 'flathub':
                self.assertEqual(len(e['id'].split('.')) >= 3, True, e['id'])
            if e['after']:
                self.assertEqual(e['source'], 'fedora')
        names = {e['name'] for e in entries}
        self.assertTrue({'Input Remapper', 'Jellyfin'} <= names)

    def test_fedora_entries_install_every_package_and_enable_services(self):
        from prosperus.installer import after_commands, install_command
        from prosperus.recommended import is_installed, recommended
        piper = next(e for e in recommended() if e['name'] == 'Piper')
        self.assertEqual(install_command(piper)[-2:], ['piper', 'libratbag-ratbagd'])
        self.assertEqual(after_commands(piper), [['sudo', '-n', 'systemctl', 'enable', '--now', 'ratbagd']])
        self.assertFalse(is_installed(piper, set(), {'piper'}))
        self.assertTrue(is_installed(piper, set(), {'piper', 'libratbag-ratbagd'}))


class SpanishImageTests(unittest.TestCase):
    def test_base_image_keeps_spanish_translations(self):
        from pathlib import Path
        text = (Path(__file__).parents[1] / 'image/Containerfile.base').read_text(encoding='utf-8')
        self.assertIn('qt6-qttranslations', text)
        self.assertLess(text.index('%_install_langs en_US:es_ES:es'), text.index('dnf -y'))
