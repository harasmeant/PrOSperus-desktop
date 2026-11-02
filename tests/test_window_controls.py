# SPDX-License-Identifier: GPL-3.0-only
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QWidget
from prosperus.window_controls import HoverControls
from prosperus import window_handle as wh


def con(ident, app_id, rect, focused=False, **extra):
    return dict(id=ident, type='floating_con', app_id=app_id, focused=focused,
                rect=dict(zip('x y width height'.split(), rect)), **extra)


def tree(*workspaces):
    return {'type': 'root', 'nodes': [{'type': 'output', 'nodes': list(workspaces)}]}


def ws(name, *nodes):
    return {'type': 'workspace', 'name': name, 'rect': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
            'nodes': [], 'floating_nodes': list(nodes)}


class HoverControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_small_at_rest_and_every_dot_is_clickable(self):
        host = QWidget(); controls = HoverControls(host, watch=host)
        self.assertFalse(controls.expanded())
        fired = []; controls.triggered.connect(fired.append)
        for (action, _, _), rect in zip(controls.buttons, controls._rects()):
            self.assertLess(rect.width(), 10)
            self.assertEqual(controls.action_at(rect.center()), action)
        self.assertIsNone(controls.action_at(QPointF(0, 0)))

    def test_expanded_buttons_are_larger_and_do_not_overlap(self):
        controls = HoverControls(actions=('maximize', 'close'))
        controls._set_progress(1.0)
        a, b = controls._rects()
        self.assertGreater(a.width(), 20)
        self.assertFalse(a.intersects(b))
        self.assertEqual([x[0] for x in controls.buttons], ['maximize', 'close'])


    def test_click_fires_only_when_released_on_the_pressed_button(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        controls = HoverControls(); controls.show()
        fired = []; controls.triggered.connect(fired.append)
        close, minimize = controls._rects()[2].center().toPoint(), controls._rects()[0].center().toPoint()
        QTest.mousePress(controls, Qt.MouseButton.LeftButton, pos=close)
        QTest.mouseRelease(controls, Qt.MouseButton.LeftButton, pos=minimize)
        self.assertEqual(fired, [])
        QTest.mouseClick(controls, Qt.MouseButton.LeftButton, pos=close)
        self.assertEqual(fired, ['close'])
        self.assertIsNone(controls.pressed)

    def test_maximize_turns_into_restore(self):
        controls = HoverControls()
        controls.set_maximized(True)
        self.assertIn('Restaurar', controls.toolTip())
        controls._set_progress(1.0); controls.grab()  # pinta el símbolo de restaurar sin errores
        controls.set_maximized(False)
        self.assertIn('Ampliar', controls.toolTip())


class HandleTests(unittest.TestCase):
    def test_target_skips_desktop_handle_hidden_and_fullscreen(self):
        t = tree(ws('General', con(1, 'org.prosperus.Desktop', (0, 0, 1920, 1080)),
                    con(2, 'foot', (100, 50, 800, 600), focused=True)),
                 ws('General · ocultas', con(3, 'gimp', (0, 0, 10, 10))))
        node, space = wh.find_target(t)
        self.assertEqual((node['id'], space['name']), (2, 'General'))
        t = tree(ws('General', con(2, 'foot', (0, 0, 1, 1), focused=True, fullscreen_mode=1)))
        self.assertEqual(wh.find_target(t), (None, None))

    def test_focus_on_handle_keeps_previous_target(self):
        t = tree(ws('General', con(2, 'foot', (0, 0, 800, 600)), con(9, wh.HANDLE_ID, (0, 0, 90, 30), focused=True)))
        self.assertEqual(wh.find_target(t, previous=2)[0]['id'], 2)
        self.assertEqual(wh.find_target(t), (None, None))

    def test_position_and_commands(self):
        self.assertEqual(wh.handle_position({'x': 100, 'y': 50, 'width': 800, 'height': 600}, 100), (450, 52))
        # Con sitio encima, la píldora no tapa la ventana; pegada arriba, va dentro.
        self.assertEqual(wh.handle_position({'x': 100, 'y': 50, 'width': 800, 'height': 600}, 100, 32, 0), (450, 16))
        self.assertEqual(wh.handle_position({'x': 100, 'y': 12, 'width': 800, 'height': 600}, 100, 32, 0), (450, 14))
        node = con(2, 'foot', (100, 50, 800, 600)); space = ws('Mi "proy"')
        saved = {}
        self.assertIn('resize set width 1920 px height 1080 px', wh.maximize_commands(node, space, saved))
        self.assertIn('move absolute position 100 px 50 px', wh.maximize_commands(node, space, saved))
        self.assertEqual(saved, {})
        self.assertEqual(wh.minimize_command(node, space), '[con_id=2] move container to workspace "Mi proy · ocultas"')


if __name__ == '__main__':
    unittest.main()


class WindowHeaderSwayTests(unittest.TestCase):
    def test_header_maximizes_through_sway(self):
        import os
        from unittest import mock
        from PySide6.QtWidgets import QApplication, QWidget
        from prosperus import window_session
        from prosperus.window_header import WindowHeader

        app = QApplication.instance() or QApplication([])
        window = QWidget()
        window.setWindowTitle('Ramas')
        header = WindowHeader('Ramas', window)

        tree = {
            'type': 'root',
            'nodes': [
                {
                    'type': 'workspace',
                    'name': 'General',
                    'rect': {'x': 0, 'y': 0, 'width': 1600, 'height': 900},
                    'nodes': [
                        {
                            'type': 'floating_con',
                            'id': 5,
                            'pid': os.getpid(),
                            'name': 'Ramas',
                            'rect': {'x': 100, 'y': 80, 'width': 900, 'height': 700},
                            'nodes': []
                        }
                    ]
                }
            ]
        }

        sent = []

        def fake(kind, payload=''):
            if kind == 4:
                return tree
            else:
                sent.append(payload)
                return [{'success': True}]

        with mock.patch.dict(os.environ, {'SWAYSOCK': '/tmp/x'}), mock.patch.object(window_session, 'request', side_effect=fake):
            header.toggle_maximized()
            header.toggle_maximized()

        self.assertEqual(len(sent), 2)
        self.assertIn('width 1600 px height 900 px', sent[0])
        self.assertIn('width 900 px height 700 px', sent[1])
        self.assertIn('[con_id=5]', sent[0])
