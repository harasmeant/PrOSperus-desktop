# SPDX-License-Identifier: GPL-3.0-only
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
