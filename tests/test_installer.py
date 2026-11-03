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
