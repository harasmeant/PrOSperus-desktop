# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
"""Fondos por horas y tonos."""
import json
import tempfile
import unittest
from pathlib import Path

from prosperus.wallpaper_schedule import blend, load, next_change, save, scene


class BlendTests(unittest.TestCase):
    def test_current_is_last_started_hour_and_wraps_midnight(self):
        hours = [7, 13, 20]
        self.assertEqual(blend(hours, 6 * 60, 0), (1, 2, 1.0))      # antes de las 7: sigue la de las 20
        self.assertEqual(blend(hours, 8 * 60, 0), (2, 0, 1.0))
        self.assertEqual(blend(hours, 23 * 60, 30), (1, 2, 1.0))

    def test_fades_during_the_first_minutes(self):
        self.assertEqual(blend([7, 20], 7 * 60, 30), (1, 0, 0.0))
        self.assertEqual(blend([7, 20], 7 * 60 + 15, 30), (1, 0, 0.5))
        self.assertEqual(blend([7, 20], 7 * 60 + 45, 30), (1, 0, 1.0))
        self.assertEqual(blend([7], 7 * 60, 30), (0, 0, 1.0))


class ConfigTests(unittest.TestCase):
    def test_load_rejects_paths_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / '.fondo.json').write_text(json.dumps({'fundido': 999, 'horas': [
                {'hora': 20, 'imagen': None, 'tono': 'noche'}, {'hora': 7, 'imagen': '../fuera.jpg'},
                {'hora': 20, 'imagen': 'otra.jpg'}, {'hora': 25}, {'hora': 9, 'imagen': 'wallpaper-09.jpg'}]}))
            data = load(tmp)
            self.assertEqual(data['fundido'], 120)
            self.assertEqual([(e['hora'], e['imagen'], e['tono']) for e in data['horas']],
                             [(9, 'wallpaper-09.jpg', 'fondo'), (20, None, 'noche')])

    def test_scene_uses_hour_images_and_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); base = folder / 'wallpaper.png'; base.write_bytes(b'x')
            (folder / 'wallpaper-07.png').write_bytes(b'y')
            save(folder, {'fundido': 20, 'horas': [{'hora': 7, 'imagen': 'wallpaper-07.png', 'tono': 'amanecer'},
                                                   {'hora': 19, 'imagen': None, 'tono': 'atardecer'}]})
            self.assertEqual(scene(folder, base, 7 * 60 + 10), (base, 'atardecer', folder / 'wallpaper-07.png', 'amanecer', .5))
            self.assertEqual(next_change(folder, 18 * 60), 60)
            self.assertEqual(scene(folder / 'nada', base, 0), (base, 'fondo', base, 'fondo', 1.0))


class ToneTests(unittest.TestCase):
    def test_every_tone_has_a_palette_and_a_recipe(self):
        from PySide6.QtWidgets import QApplication
        from prosperus.tones import GROUPS, TONES
        QApplication.instance() or QApplication([])
        self.assertGreaterEqual(len(TONES), 20)
        for tone in TONES.values():
            self.assertIn(tone.group, GROUPS)
            palette = tone.palette()
            self.assertTrue(palette.accent.startswith('#') and palette.base.startswith('#'))
            targets, neutral = tone.recipe
            self.assertEqual(len(targets), 2)
        self.assertIn('atardecer', TONES)

    def test_toned_wallpaper_is_cached_and_keeps_size(self):
        import os
        from PySide6.QtGui import QColor, QImage
        from PySide6.QtWidgets import QApplication
        from prosperus import tones
        QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            os.environ['XDG_CACHE_HOME'] = tmp
            source = Path(tmp) / 'fondo.png'
            image = QImage(64, 40, QImage.Format.Format_RGB32); image.fill(QColor('#7a1d28')); image.save(str(source))
            first = tones.toned_wallpaper(source, 'verdes')
            self.assertNotEqual(first, source)
            self.assertEqual(tones.toned_wallpaper(source, 'verdes'), first)
            result = QImage(str(first)); self.assertEqual((result.width(), result.height()), (64, 40))
            self.assertGreater(QColor(result.pixel(5, 5)).green(), QColor(result.pixel(5, 5)).red())
            self.assertEqual(tones.toned_wallpaper(source, 'fondo'), source)


class PickerTests(unittest.TestCase):
    def test_add_and_remove_hours_copy_and_clean_images(self):
        from prosperus.wallpaper_picker import add_hour, remove_hour
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'proyecto'; folder.mkdir()
            (folder / 'wallpaper.png').write_bytes(b'base')
            source = Path(tmp) / 'tarde.jpg'; source.write_bytes(b'tarde')
            self.assertEqual(add_hour(folder, 19, source, 'atardecer'), folder / 'wallpaper-19.jpg')
            self.assertEqual(add_hour(folder, 7, None, 'amanecer'), folder / 'wallpaper.png')
            self.assertEqual([(e['hora'], e['imagen']) for e in load(folder)['horas']], [(7, None), (19, 'wallpaper-19.jpg')])
            remove_hour(folder, 19)
            self.assertFalse((folder / 'wallpaper-19.jpg').exists())

    def test_hour_images_are_not_documents(self):
        from prosperus.model import is_wallpaper_name
        self.assertTrue(is_wallpaper_name('wallpaper-07') and is_wallpaper_name('wallpaper'))
        self.assertFalse(is_wallpaper_name('wallpaper-tarde'))


class LivingWallpaperTests(unittest.TestCase):
    def test_cover_crop_fills_without_stretching(self):
        from prosperus.living_wallpaper import cover_crop
        self.assertEqual(cover_crop((1600, 1000), (1600, 1000)), (0.0, 0.0, 1.0, 1.0))
        x, y, w, h = cover_crop((2000, 1000), (1000, 1000))   # imagen ancha en pantalla cuadrada: recorta los lados
        self.assertAlmostEqual(w, .5); self.assertAlmostEqual(x, .25); self.assertEqual((y, h), (0.0, 1.0))

    def test_living_wallpaper_is_off_by_default(self):
        from PySide6.QtCore import QSettings
        settings = QSettings(tempfile.mktemp(suffix='.ini'), QSettings.Format.IniFormat)
        self.assertFalse(settings.value('fondo/animado', False, type=bool))
