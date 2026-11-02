# SPDX-License-Identifier: GPL-3.0-only
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from PySide6.QtWidgets import QApplication
from prosperus import display_settings as ds

SWAY = json.dumps([
    {'name': 'eDP-1', 'make': 'BOE', 'model': '0x0BCA', 'active': True, 'scale': 2.0,
     'current_mode': {'width': 2560, 'height': 1600}},
    {'name': 'HDMI-A-1', 'make': 'Dell', 'model': 'U2720Q', 'active': True, 'scale': 1.0,
     'current_mode': {'width': 1920, 'height': 1080}},
    {'name': 'DP-2', 'active': False, 'modes': [{'width': 1280, 'height': 1024}]},
])


class DisplaySettingsTests(unittest.TestCase):
    def setUp(self):
        self.outputs = ds.parse_outputs(SWAY)

    def test_parse_uses_current_or_first_mode(self):
        self.assertEqual([o['name'] for o in self.outputs], ['eDP-1', 'HDMI-A-1', 'DP-2'])
        self.assertEqual(self.outputs[1]['description'], 'Dell U2720Q')
        self.assertEqual((self.outputs[2]['width'], self.outputs[2]['scale'], self.outputs[2]['description']),
                         (1280, 1.0, 'DP-2'))

    def test_extend_right_uses_logical_widths(self):
        self.assertEqual(ds.plan_commands(self.outputs, 'extend', 'eDP-1', 'right'), [
            'output "eDP-1" enable pos 0 0', 'output "HDMI-A-1" enable pos 1280 0',
            'output "DP-2" enable pos 3200 0'])

    def test_extend_left_and_above(self):
        self.assertEqual(ds.plan_commands(self.outputs[:2], 'extend', 'HDMI-A-1', 'left'),
                         ['output "HDMI-A-1" enable pos 0 0', 'output "eDP-1" enable pos -1280 0'])
        self.assertEqual(ds.plan_commands(self.outputs[:2], 'extend', 'eDP-1', 'above'),
                         ['output "eDP-1" enable pos 0 0', 'output "HDMI-A-1" enable pos 0 -1080'])

    def test_single_disables_others_and_unknown_primary_falls_back(self):
        self.assertEqual(ds.plan_commands(self.outputs[:2], 'single', 'nope', 'right'),
                         ['output "eDP-1" enable pos 0 0', 'output "HDMI-A-1" disable'])

    def test_mirror_targets_secondary_outputs(self):
        self.assertEqual(ds.mirror_commands(self.outputs[:2], 'eDP-1'),
                         [['wl-mirror', '--fullscreen-output', 'HDMI-A-1', 'eDP-1']])

    def test_config_round_trip_and_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sub/displays.json'
            self.assertEqual(ds.load_config(path), ds.DEFAULTS)
            ds.save_config({'mode': 'mirror', 'primary': 'eDP-1', 'position': 'left'}, path)
            self.assertEqual(ds.load_config(path)['mode'], 'mirror')
            path.write_text('{roto')
            self.assertEqual(ds.load_config(path), ds.DEFAULTS)

    def test_apply_without_sway_reports_it(self):
        with mock.patch.object(ds, 'read_outputs', return_value=[]):
            self.assertIn('No se detectan', ds.apply(dict(ds.DEFAULTS)))

    def test_dialog_lists_outputs_and_builds_config(self):
        QApplication.instance() or QApplication([])
        with mock.patch.object(ds, 'load_config', return_value=dict(ds.DEFAULTS, primary='HDMI-A-1')):
            dialog = ds.DisplayDialog(outputs=self.outputs[:2])
        self.assertEqual(dialog.primary_choice.count(), 2)
        self.assertEqual(dialog.current_config(), {'mode': 'extend', 'primary': 'HDMI-A-1', 'position': 'right'})
        dialog.mode_choice.setCurrentIndex(dialog.mode_choice.findData('mirror'))
        self.assertFalse(dialog.position_choice.isEnabled())


if __name__ == '__main__':
    unittest.main()
