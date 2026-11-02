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


class VaultMoveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'vault'
        (self.root / 'Proyecto/Apuntes').mkdir(parents=True)
        (self.root / 'Proyecto/Apuntes/Árbol.md').write_text('# Árbol')
        (self.root / 'Proyecto/Inicio.md').write_text('# Inicio')
        (self.root / 'Otro').mkdir()
        (self.root / '.oculta').mkdir()
        self.vault = Vault(self.root)

    def test_folders_root_first_without_hidden(self):
        names = [str(p.relative_to(self.root)) for p in self.vault.folders()]
        self.assertEqual(names, ['.', 'Otro', 'Proyecto', 'Proyecto/Apuntes'])

    def test_move_note_and_folder(self):
        note = self.vault.move(self.root / 'Proyecto/Inicio.md', self.root / 'Otro')
        self.assertEqual(note.read_text(), '# Inicio')
        folder = self.vault.move(self.root / 'Proyecto/Apuntes', self.root / 'Otro')
        self.assertTrue((folder / 'Árbol.md').is_file())
        self.assertFalse((self.root / 'Proyecto/Apuntes').exists())

    def test_rejected_moves_change_nothing(self):
        (self.root / 'Otro/Inicio.md').write_text('otra')
        with self.assertRaises(FileExistsError):
            self.vault.move(self.root / 'Proyecto/Inicio.md', self.root / 'Otro')
        with self.assertRaisesRegex(ValueError, 'sí misma'):
            self.vault.move(self.root / 'Proyecto', self.root / 'Proyecto/Apuntes')
        with self.assertRaisesRegex(ValueError, 'Ya está'):
            self.vault.move(self.root / 'Proyecto/Inicio.md', self.root / 'Proyecto')
        with self.assertRaises(ValueError):
            self.vault.move(self.root, self.root / 'Otro')
        self.assertEqual((self.root / 'Proyecto/Inicio.md').read_text(), '# Inicio')
        self.assertEqual((self.root / 'Otro/Inicio.md').read_text(), 'otra')


class WallpaperTests(unittest.TestCase):
    def test_apply_wallpaper_keeps_previous_and_hue_follows_image(self):
        from PySide6.QtGui import QColor, QImage
        from prosperus.appearance import wallpaper_hue
        from prosperus.wallpaper_picker import apply_wallpaper
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'Proyecto'; folder.mkdir()
            (folder / 'wallpaper.png').write_bytes(b'antes')
            source = Path(temp) / 'azul.jpg'
            image = QImage(8, 8, QImage.Format.Format_RGB32); image.fill(QColor.fromHsv(220, 200, 200)); image.save(str(source))
            target = apply_wallpaper(source, folder)
            self.assertEqual(target.name, 'wallpaper.jpg')
            self.assertEqual((folder / '.wallpaper-anterior.png').read_bytes(), b'antes')
            self.assertFalse((folder / 'wallpaper.png').exists())
            self.assertAlmostEqual(wallpaper_hue(target, 0), 220, delta=4)
            with self.assertRaises(ValueError):
                apply_wallpaper(source, Path.home())


class QuickSettingsTests(unittest.TestCase):
    def test_parsers_read_system_tools_output(self):
        from prosperus.quick_settings import parse_brightness, parse_powered, parse_volume
        self.assertEqual(parse_volume('Volume: 0.29 [MUTED]'), (29, True))
        self.assertEqual(parse_volume('Volume: 1.00'), (100, False))
        self.assertIsNone(parse_volume(None))
        self.assertEqual(parse_brightness('intel_backlight,backlight,120,40%,300'), 40)
        self.assertIsNone(parse_brightness(''))
        self.assertTrue(parse_powered('Controller 00:11 (public)\n\tPowered: yes\n'))
        self.assertIsNone(parse_powered('No default controller available'))

    def test_panel_applies_state_without_bluetooth(self):
        from PySide6.QtWidgets import QApplication
        from prosperus.appearance import Palette
        from prosperus.quick_settings import QuickSettings
        app = QApplication.instance() or QApplication([])
        shell = type('Shell', (), {'colors': Palette(120)})()
        panel = QuickSettings(shell)
        panel.apply({'brightness': None, 'volume': (35, False), 'wifi': 'enabled', 'connections': 'lo\nCasa',
                     'bluetooth': None, 'mode': 'default'})
        self.assertFalse(panel.brightness.isEnabled())
        self.assertEqual(panel.volume.value(), 35)
        self.assertEqual(panel.wifi_conn.text(), 'Casa')
        self.assertEqual(panel.bluetooth.text(), 'No disponible')

    def test_sliders_apply_on_any_change_but_not_when_reading(self):
        from unittest import mock
        from PySide6.QtWidgets import QApplication
        from prosperus import quick_settings
        from prosperus.appearance import Palette
        app = QApplication.instance() or QApplication([])
        panel = quick_settings.QuickSettings(type('Shell', (), {'colors': Palette(120)})())
        calls = []
        with mock.patch.object(quick_settings, 'attempt', side_effect=lambda argv: (calls.append(argv) or (True, ''))):
            panel.apply({'brightness': 50, 'volume': (40, False), 'wifi': None, 'connections': '',
                         'bluetooth': None, 'mode': 'default'})
            self.assertFalse(panel.br_timer.isActive() or panel.vol_timer.isActive())
            panel.brightness.setValue(70); panel.volume.setValue(20)  # clic, rueda o flechas
            self.assertTrue(panel.br_timer.isActive())
            panel.br_timer.stop(); panel._set_br(); panel.vol_timer.stop(); panel._set_vol()
        self.assertIn('70%', calls[0]); self.assertIn('0.20', calls[1])
        with mock.patch.object(quick_settings.subprocess, 'run', side_effect=FileNotFoundError):
            panel._set_br()
        self.assertFalse(panel.br_err.isHidden())


class LinkLayoutTests(unittest.TestCase):
    def test_wallpaper_traits_and_procedural_branch(self):
        import tempfile
        from pathlib import Path
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QColor, QImage, QPainter
        from prosperus.appearance import wallpaper_traits
        from prosperus.branches import branch
        with tempfile.TemporaryDirectory() as folder:
            # Rejilla de líneas rectas: fondo «técnico»; degradado liso: orgánico.
            grid = QImage(160, 100, QImage.Format.Format_RGB32); grid.fill(QColor('black'))
            painter = QPainter(grid); painter.setPen(QColor('white'))
            for x in range(0, 160, 16):
                painter.drawLine(x, 0, x, 100)
            painter.end()
            path = Path(folder) / 'grid.png'; grid.save(str(path))
            plain = QImage(160, 100, QImage.Format.Format_RGB32); plain.fill(QColor('#203020'))
            flat = Path(folder) / 'flat.png'; plain.save(str(flat))
            technical, organic = wallpaper_traits(path, 0), wallpaper_traits(flat, 0)
            self.assertGreater(technical['straight'], .5)
            self.assertEqual(organic['straight'], 0)
            self.assertEqual(organic['magic'], 0)
            amber = QImage(160, 100, QImage.Format.Format_RGB32); amber.fill(QColor('#a0601c'))
            warm = Path(folder) / 'amber.png'; amber.save(str(warm))
            self.assertGreater(wallpaper_traits(warm, 0)['magic'], .9)
            canvas = QImage(300, 200, QImage.Format.Format_ARGB32); canvas.fill(0)
            painter = QPainter(canvas)
            for traits in (technical, organic, None):
                branch(painter, QPointF(20, 100), QPointF(280, 100), 7, 2, QColor('white'), 1, 5, traits=traits)
            painter.end()

    def test_branch_style_saves_inherits_validates_and_resets(self):
        import tempfile
        from pathlib import Path
        from prosperus import branch_style
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); child = root / 'Proyecto' / 'Sub'; child.mkdir(parents=True)
            self.assertEqual(branch_style.load(child, root), {})
            branch_style.save(root / 'Proyecto', {'auto': False, 'straight': 3, 'magic': .5, 'detail': 'x',
                                                  'curl': 9, 'opacity': .8, 'otra': 1})
            # La subcarpeta hereda; los valores se recortan a su rango y se ignora lo desconocido.
            self.assertEqual(branch_style.load(child, root),
                             {'straight': 1.0, 'magic': .5, 'curl': 2.5, 'opacity': .8})
            branch_style.save(child, {'auto': True, 'straight': 1, 'width': 2})
            self.assertEqual(branch_style.load(child, root), {'width': 2.0})  # en automático no fija el estilo
            merged = branch_style.merge({'straight': .2, 'seed': 4}, branch_style.load(child, root))
            self.assertEqual(merged, {'straight': .2, 'seed': 4, 'width': 2.0})
            branch_style.reset(child); branch_style.reset(child)
            self.assertIn('straight', branch_style.load(child, root))  # vuelve a heredar de arriba
            with self.assertRaises(ValueError):
                branch_style.save(root / 'no-existe', {})
            # Gradiente de la rama: aparte de los adornos y solo si está activado.
            self.assertNotIn('branch_gradient', branch_style.clean({'opacity_end': .2, 'light': 1}))
            gradient = branch_style.clean({'branch_gradient': True, 'opacity': .8, 'opacity_end': .2, 'light': 5, 'light_end': -.5})
            self.assertEqual(gradient['branch_gradient'], {'alpha_end': .25, 'light': 1.0, 'light_end': -.5})
            from PySide6.QtCore import QPointF
            from PySide6.QtGui import QColor, QImage, QPainter
            from prosperus.branches import branch
            canvas = QImage(300, 120, QImage.Format.Format_ARGB32); canvas.fill(0)
            painter = QPainter(canvas)
            branch(painter, QPointF(10, 60), QPointF(290, 60), 12, 10, QColor(200, 200, 200), 0, 0, 0, gradient)
            painter.end()
            self.assertGreater(canvas.pixelColor(20, 60).alpha(), canvas.pixelColor(280, 60).alpha())

    def test_branch_ornaments_images_frequency_and_safety(self):
        import tempfile
        from pathlib import Path
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QColor, QImage, QPainter
        from prosperus import branch_style
        from prosperus.branches import branch
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); folder = root / 'Fantasia'; folder.mkdir()
            picture = root / 'jake.png'
            image = QImage(32, 32, QImage.Format.Format_ARGB32); image.fill(QColor('orange')); image.save(str(picture))
            name = branch_style.add_image(folder, picture)
            self.assertEqual(name, 'jake.png'); self.assertEqual(branch_style.add_image(folder, folder / '.prosperus-adornos' / name), name)
            self.assertEqual(branch_style.add_image(folder, picture), 'jake-2.png')  # mismo nombre, otra copia
            with self.assertRaises(ValueError):
                branch_style.add_image(folder, root / 'nota.md')
            branch_style.save(folder, {'ornaments': [
                {'kind': 'pluma', 'density': 7, 'angle': 400, 'angle_end': -5, 'size': 9, 'side': 'raro',
                 'order': 'dentro', 'place': 'raro', 'opacity': .5},
                {'kind': 'imagen', 'file': '../../jake.png', 'every': 2, 'place': 'brote', 'tint': False},
                {'kind': 'imagen', 'file': 'no-existe.png'}, {'kind': 'bomba'}]})
            ornaments = branch_style.load(folder, root)['ornaments']
            # Valores recortados a su rango; sin «_end» no hay gradiente; solo vale el nombre dentro de .prosperus-adornos.
            self.assertEqual([o['kind'] for o in ornaments], ['pluma', 'imagen'])
            feather = ornaments[0]
            self.assertEqual((feather['density'], feather['angle'], feather['angle_end'], feather['size'], feather['size_end']),
                             (1.0, 180.0, 0.0, 3.0, 3.0))
            self.assertEqual((feather['side'], feather['order'], feather['place'], feather['opacity_end']), ('horario', 'dentro', 'rama', .5))
            self.assertAlmostEqual(ornaments[1]['density'], .3)  # ajustes antiguos: 1 de cada 2 brotes
            self.assertEqual(ornaments[1]['path'], folder / '.prosperus-adornos' / 'jake.png')
            self.assertFalse(ornaments[1]['tint'])
            from prosperus.branches import ornament_spacing
            self.assertIsNone(ornament_spacing(0)); self.assertEqual(ornament_spacing(1), 6)
            canvas = QImage(300, 200, QImage.Format.Format_ARGB32); canvas.fill(0)
            painter = QPainter(canvas)
            branch(painter, QPointF(20, 100), QPointF(280, 100), 7, 2, QColor('white'), 1, 6, traits={'ornaments': ornaments})
            painter.end()

    def test_branch_settings_window_builds_preview(self):
        import os, tempfile
        from pathlib import Path
        from PySide6.QtWidgets import QApplication
        from prosperus.branch_settings import BranchSettings
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            window = BranchSettings(Path(folder))
            window.auto.setChecked(False); window.sliders['straight'].setValue(100)
            self.assertEqual(window.preview.traits['straight'], 1.0)
            window.add_ornament({'kind': 'pluma'})
            window.bars['angle'].setValue(90); window.side.setCurrentIndex(window.side.findData('ambos'))
            window.gradient.setChecked(True); window.bars_end['size'].setValue(200)
            feather = window.preview.traits['ornaments'][0]
            self.assertEqual((feather['angle'], feather['side'], feather['size_end']), (90, 'ambos', 2.0))
            window.gradient.setChecked(False)
            self.assertEqual(window.preview.traits['ornaments'][0]['size_end'], feather['size'])
            window.grab()
            window.save()
            self.assertTrue((Path(folder) / '.prosperus-ramas.json').is_file())

    def test_map_metrics_keep_proportions_on_wide_screens(self):
        from prosperus.map_layout import map_metrics
        for width, height in ((1880, 800), (1240, 600), (2520, 800), (3400, 1160), (5080, 1080), (980, 520)):
            m = map_metrics(width, height)
            # La elipse cabe en la superficie y no se estira más de 2,3 veces su alto (21:9, 32:9).
            self.assertLessEqual(m['rx'] + m['nw'] / 2, width / 2)
            self.assertLessEqual(m['rx'], max(m['ry'] * 2.3, m['cw'] / 2 + m['nw'] / 2 + 24) + 1e-9)
            self.assertGreater(m['rx'], m['cw'] / 2)

    def test_concentric_slots_do_not_overlap_and_links_stay_adjacent(self):
        from prosperus.map_layout import concentric_slots, link_order
        slots = concentric_slots(12, 640, 300, 226, 116, 190, 108)
        self.assertGreaterEqual(len(slots), 12)
        for i, a in enumerate(slots):
            for b in slots[i + 1:]:
                self.assertTrue(abs(a[0] - b[0]) >= 190 or abs(a[1] - b[1]) >= 108, (a, b))
        order = link_order(5, {(0, 3): 2, (3, 4): 1})
        self.assertEqual(order[:3], [3, 0, 4])

    def test_links_skip_code_and_force_pulls_linked_nodes_together(self):
        from prosperus.map_layout import ellipse_points, force_layout
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'v'; (root / 'A').mkdir(parents=True); (root / 'B').mkdir()
            (root / 'A/uno.md').write_text('Ver [[dos]] y [tres](../B/tres.md) `[[nada]]` [web](https://x.org)')
            (root / 'A/dos.md').write_text('# dos'); (root / 'B/tres.md').write_text('# tres')
            vault = Vault(root)
            self.assertEqual(vault.links(root / 'A/uno.md'), {root / 'A/dos.md', root / 'B/tres.md'})
        points = ellipse_points(4, 0, 0, 300, 200)
        moved = force_layout(points, {(0, 2): 5}, 0, 0, 300, 200)
        dist = lambda p, q: ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** .5
        self.assertLess(dist(moved[0], moved[2]), dist(points[0], points[2]))
        self.assertEqual(force_layout(points, {}, 0, 0, 300, 200), points)


class InstallerTests(unittest.TestCase):
    def test_commands_parsing_and_rejections(self):
        from prosperus.installer import install_command, parse_dnf, parse_flatpak, search_commands
        self.assertEqual(search_commands('rm -rf; ls'), [])
        self.assertEqual([s for s, _ in search_commands('blender')], ['fedora', 'flathub'])
        self.assertEqual(parse_dnf('blender\t3D\nblender\t3D\n\n')[0]['id'], 'blender')
        self.assertEqual(len(parse_dnf('blender\t3D\nblender\t3D\n')), 1)
        self.assertEqual(parse_flatpak('org.blender.Blender\tBlender\t3D\nNo matches found\n')[0]['id'], 'org.blender.Blender')
        self.assertEqual(install_command({'source': 'file', 'id': '/tmp/x.rpm'})[-1], '/tmp/x.rpm')
        with self.assertRaises(ValueError):
            install_command({'source': 'file', 'id': '/tmp/x.sh'})


class RenameTrashTests(unittest.TestCase):
    def test_rename_wikilinks_rules(self):
        from prosperus.model import rename_wikilinks
        text = '[[Plan]] [[plan|el plan]] [[Ideas/Plan#Fechas]] [[Plan.md]] [[Planta]] `[[Plan]]`\n```\n[[Plan]]\n```'
        result, count = rename_wikilinks(text, 'Plan', 'Plan 2026')
        self.assertEqual(count, 4)
        self.assertEqual(result, '[[Plan 2026]] [[Plan 2026|el plan]] [[Ideas/Plan 2026#Fechas]] [[Plan 2026.md]] '
                                 '[[Planta]] `[[Plan]]`\n```\n[[Plan]]\n```')

    def test_vault_rename_updates_links_and_trash_keeps_files(self):
        import tempfile
        from pathlib import Path
        from prosperus.model import Vault
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'A').mkdir()
            (root / 'A' / 'Plan.md').write_text('# Plan\n', encoding='utf-8')
            (root / 'Indice.md').write_text('Ver [[Plan]] y [[Otra]]\n', encoding='utf-8')
            vault = Vault(root)
            target, updated = vault.rename(root / 'A' / 'Plan.md', 'Plan 2026')
            self.assertEqual(target, root / 'A' / 'Plan 2026.md')
            self.assertEqual((root / 'Indice.md').read_text(encoding='utf-8'), 'Ver [[Plan 2026]] y [[Otra]]\n')
            self.assertEqual(updated, [root / 'Indice.md'])
            with self.assertRaises(FileExistsError):
                vault.rename(root / 'A', 'A')  # nunca sobrescribe
            folder, _ = vault.rename(root / 'A', 'B')
            self.assertTrue((root / 'B' / 'Plan 2026.md').is_file())
            first = vault.trash(root / 'Indice.md')
            (root / 'Indice.md').write_text('otra\n', encoding='utf-8')
            second = vault.trash(root / 'Indice.md')
            self.assertEqual({first.name, second.name}, {'Indice.md', 'Indice (2).md'})
            self.assertNotIn(first, list(vault.notes()))  # la papelera está oculta
            with self.assertRaises(ValueError):
                vault.trash(root / '.papelera')
            with self.assertRaises(ValueError):
                vault.rename(root, 'x')

    def test_trash_remembers_origin_and_restores_without_overwriting(self):
        import tempfile
        from pathlib import Path
        from prosperus.model import Vault
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'A').mkdir()
            note = root / 'A' / 'n.md'; note.write_text('uno\n', encoding='utf-8')
            vault = Vault(root)
            vault.trash(note)
            note.write_text('dos\n', encoding='utf-8')  # otra nota con el mismo nombre ocupa su sitio
            self.assertEqual([origin for _, origin in vault.trashed()], ['A/n.md'])
            restored = vault.restore('n.md')
            self.assertEqual(restored, root / 'A' / 'n (2).md')
            self.assertEqual(restored.read_text(encoding='utf-8'), 'uno\n')
            self.assertEqual(note.read_text(encoding='utf-8'), 'dos\n')
            self.assertEqual(vault.trashed(), [])
            # Si la carpeta de origen ya no existe, vuelve a la raíz.
            vault.trash(root / 'A' / 'n (2).md'); vault.trash(note)
            (root / 'A').rmdir()
            self.assertEqual({vault.restore(p.name).parent for p, _ in vault.trashed()}, {root})
            with self.assertRaises(FileNotFoundError):
                vault.restore('../A')
