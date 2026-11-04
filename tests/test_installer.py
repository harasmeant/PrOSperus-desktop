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
            self.assertIn('o de Flathub, se conserva', persistence_note(marker, system))
        script = (Path(__file__).parents[1] / 'image/rootfs/usr/libexec/prosperus-persistence').read_text(encoding='utf-8')
        self.assertIn('mount --bind "$data/flatpak" "$fp"', script)
        # La marca de persistencia se crea al final, cuando ya está todo montado.
        self.assertGreater(script.index('touch /run/prosperus-persistent'), script.index('"$data/flatpak" "$fp"'))


class RecommendedTests(unittest.TestCase):
    def test_catalog_is_consistent(self):
        from prosperus.recommended import recommended
        entries = recommended()
        ids = [str(e['id']) for e in entries]
        self.assertEqual(len(ids), len(set(ids)))
        for e in entries:
            self.assertIn(e['source'], ('system', 'flathub'))
            if isinstance(e['id'], dict):
                self.assertEqual(set(e['id']), {'arch', 'fedora'})
            if e['source'] == 'flathub':
                self.assertEqual(len(e['id'].split('.')) >= 3, True, e['id'])
            if e['after']:
                self.assertEqual(e['source'], 'system')
        names = {e['name'] for e in entries}
        self.assertTrue({'Input Remapper', 'Jellyfin'} <= names)

    def test_fedora_entries_install_every_package_and_enable_services(self):
        from prosperus.distro import ARCH, FEDORA
        from prosperus.installer import after_commands, install_command
        from prosperus.recommended import is_installed, recommended
        piper = next(e for e in recommended() if e['name'] == 'Piper')
        self.assertEqual(install_command(piper, FEDORA)[-2:], ['piper', 'libratbag-ratbagd'])
        self.assertEqual(install_command(piper, ARCH), ['sudo', '-n', 'pacman', '-Syu', '--noconfirm', '--needed',
                                                        'piper', 'libratbag'])
        self.assertEqual(after_commands(piper), [['sudo', '-n', 'systemctl', 'enable', '--now', 'ratbagd']])
        self.assertFalse(is_installed(piper, set(), {'piper'}, FEDORA))
        self.assertTrue(is_installed(piper, set(), {'piper', 'libratbag-ratbagd'}, FEDORA))
        self.assertTrue(is_installed(piper, set(), {'piper', 'libratbag'}, ARCH))


class DistroTests(unittest.TestCase):
    def test_detects_arch_and_derivatives_and_defaults_to_fedora(self):
        import tempfile
        from pathlib import Path
        from prosperus.distro import ARCH, FEDORA, detect
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / 'os-release'
            release.write_text('NAME="Arch Linux"\nID=arch\n')
            self.assertIs(detect(release), ARCH)
            release.write_text('ID=endeavouros\nID_LIKE="arch"\n')
            self.assertIs(detect(release), ARCH)
            release.write_text('ID=fedora\n')
            self.assertIs(detect(release), FEDORA)
            self.assertIs(detect(Path(tmp) / 'falta'), FEDORA)

    def test_parses_pacman_search(self):
        from prosperus.distro import ARCH
        output = ('extra/blender 17:4.5.0-1 [instalado]\n    Suite 3D\n'
                  'extra/freecad 1.0.2-1\n    Modelado paramétrico\n')
        self.assertEqual([(i['name'], i['summary'], i['source']) for i in ARCH.parse_search(output)],
                         [('blender', 'Suite 3D', 'system'), ('freecad', 'Modelado paramétrico', 'system')])

    def test_local_packages_follow_the_distro(self):
        from prosperus.distro import ARCH, FEDORA
        from prosperus.installer import install_command
        pkg = {'source': 'file', 'id': '/tmp/x.pkg.tar.zst'}
        self.assertEqual(install_command(pkg, ARCH)[:4], ['sudo', '-n', 'pacman', '-U'])
        with self.assertRaises(ValueError):
            install_command(pkg, FEDORA)
        self.assertIn('dnf5', install_command({'source': 'file', 'id': '/tmp/x.rpm'}, FEDORA))


class SpanishImageTests(unittest.TestCase):
    def test_base_image_keeps_spanish_translations(self):
        from pathlib import Path
        text = (Path(__file__).parents[1] / 'image/Containerfile.base').read_text(encoding='utf-8')
        self.assertIn('qt6-qttranslations', text)
        self.assertLess(text.index('%_install_langs en_US:es_ES:es'), text.index('dnf -y'))

    def test_arch_image_keeps_spanish_translations(self):
        from pathlib import Path
        text = (Path(__file__).parents[1] / 'image/arch/Containerfile.base').read_text(encoding='utf-8')
        self.assertIn('qt6-translations', text)
        self.assertLess(text.index("/^NoExtract.*usr\\/share/d"), text.index('locale-gen'))
