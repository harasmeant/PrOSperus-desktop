# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import unittest

from prosperus.quick_settings import parse_sinks, parse_track

STATUS = """PipeWire 'pipewire-0' [1.4.9, user@host, cookie:1]
 └─ Clients:
        33. WirePlumber                         [1.4.9, user@host, pid:1]

Audio
 ├─ Devices:
 │      42. Built-in Audio                      [alsa]
 │
 ├─ Sinks:
 │  *   46. Built-in Audio Analog Stereo        [vol: 0.40]
 │      47. HDMI / DisplayPort 1 Output         [vol: 1.00 MUTED]
 │
 ├─ Sources:
 │  *   48. Built-in Audio Analog Stereo        [vol: 1.00]

Video
 ├─ Sinks:
 │      60. Some video sink
"""


class QuickMediaTest(unittest.TestCase):
    def test_sinks(self):
        self.assertEqual(parse_sinks(STATUS), [(46, 'Built-in Audio Analog Stereo', True),
                                               (47, 'HDMI / DisplayPort 1 Output', False)])
        self.assertEqual(parse_sinks(''), [])

    def test_track(self):
        self.assertEqual(parse_track('Playing|Queen|Bohemian Rhapsody'), (True, 'Queen · Bohemian Rhapsody'))
        self.assertEqual(parse_track('Paused||Vídeo'), (False, 'Vídeo'))
        self.assertIsNone(parse_track(None))


if __name__ == '__main__':
    unittest.main()


class BuiltinInputTests(unittest.TestCase):
    INPUTS = '''[
      {"identifier": "1:1:AT_Translated_Set_2_keyboard", "type": "keyboard", "libinput": {"send_events": "disabled"}},
      {"identifier": "1267:12541:ELAN0718:00_04F3:30FD_Touchpad", "type": "touchpad", "libinput": {"send_events": "enabled"}},
      {"identifier": "1267:12541:ELAN0718:00_04F3:30FD_Mouse", "type": "pointer", "libinput": {"send_events": "enabled"}},
      {"identifier": "5426:103:Razer_Razer_Naga_Trinity_Keyboard", "type": "keyboard", "libinput": {"send_events": "enabled"}},
      {"identifier": "14289:100:Naya_B.V._Naya_Create_Left_Mouse", "type": "pointer", "libinput": {"send_events": "enabled"}}
    ]'''

    def test_only_laptop_keyboard_and_touchpad(self):
        from prosperus.quick_settings import builtin_inputs
        self.assertEqual(builtin_inputs(self.INPUTS), [
            ('1:1:AT_Translated_Set_2_keyboard', False),
            ('1267:12541:ELAN0718:00_04F3:30FD_Touchpad', True),
            ('1267:12541:ELAN0718:00_04F3:30FD_Mouse', True)])
        self.assertEqual(builtin_inputs(None), [])
        self.assertEqual(builtin_inputs('no es json'), [])

    def test_toggle_sends_swaymsg_for_each_device(self):
        from unittest import mock
        from PySide6.QtWidgets import QApplication
        from prosperus import quick_settings
        from prosperus.appearance import Palette
        app = QApplication.instance() or QApplication([])
        panel = quick_settings.QuickSettings(type('Shell', (), {'colors': Palette(120)})())
        state = {'brightness': None, 'volume': None, 'wifi': None, 'connections': '', 'bluetooth': None,
                 'mode': '', 'builtin': quick_settings.builtin_inputs(self.INPUTS)}
        panel.apply(state)
        self.assertFalse(panel.kbd.isHidden())
        self.assertTrue(panel.kbd.isChecked())
        calls = []
        with mock.patch.object(quick_settings, 'run', side_effect=lambda argv: calls.append(argv)), \
             mock.patch.object(panel, 'refresh'):
            panel.kbd.click()
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(c[0] == 'swaymsg' and c[1].endswith('events disabled') for c in calls))
        panel.apply(dict(state, builtin=[]))
        self.assertTrue(panel.kbd.isHidden())
