# SPDX-License-Identifier: GPL-3.0-only
import unittest
from unittest.mock import patch
from prosperus.window_layouts import LayoutOptions, Rect, arrange, screen_profile
from prosperus.window_session import apply, plan, targets, DESKTOP_ID


class LayoutGeometryTests(unittest.TestCase):
    def test_spiral_turns_and_halves(self):
        boxes = arrange(Rect(0, 0, 1600, 1200), 5, LayoutOptions(gap=0), (1, 1))
        self.assertEqual(boxes, [Rect(0, 0, 800, 1200), Rect(800, 0, 800, 600),
            Rect(1200, 600, 400, 600), Rect(800, 900, 400, 300), Rect(800, 600, 400, 300)])

    def test_all_layouts_stay_inside_without_overlap(self):
        for width, height in [(1920, 1080), (3440, 1440), (5120, 1440), (1080, 1920)]:
            for mode in ('spiral', 'columns', 'centered'):
                for count in range(1, 9):
                    with self.subTest(size=(width, height), mode=mode, count=count):
                        area = Rect(-width, 100, width, height)
                        try:
                            boxes = arrange(area, count, LayoutOptions(mode, 16))
                        except ValueError:
                            continue  # Una distribución ilegible debe rechazarse, no solaparse.
                        self.assertEqual(len(boxes), count)
                        for i, r in enumerate(boxes):
                            self.assertGreaterEqual(r.x, area.x)
                            self.assertGreaterEqual(r.y, area.y)
                            self.assertLessEqual(r.x + r.width, area.x + width)
                            self.assertLessEqual(r.y + r.height, area.y + height)
                            for other in boxes[i + 1:]:
                                self.assertTrue(r.x + r.width <= other.x or other.x + other.width <= r.x
                                                or r.y + r.height <= other.y or other.y + other.height <= r.y)

    def test_ultrawide_centered_band_and_profile(self):
        boxes = arrange(Rect(0, 0, 5120, 1440), 3, LayoutOptions('centered', 12, 50, 2400))
        self.assertEqual(boxes[0].x + boxes[0].width // 2, 2560)
        self.assertEqual(screen_profile(3440, 1440), 'ultrawide')
        self.assertEqual(screen_profile(5120, 1440), 'superwide')
        self.assertEqual(screen_profile(1080, 1920), 'standard')

    def test_small_space_rejected(self):
        with self.assertRaises(ValueError):
            arrange(Rect(0, 0, 800, 400), 8, LayoutOptions())

    def test_invalid_options(self):
        for options in [LayoutOptions('unknown'), LayoutOptions(gap=-1), LayoutOptions(ratio=99)]:
            with self.assertRaises(ValueError):
                arrange(Rect(0, 0, 1920, 1080), 1, options)


class SwayPlanningTests(unittest.TestCase):
    def setUp(self):
        self.workspaces = [{'name': 'trabajo', 'output': 'DP-1', 'visible': True,
                            'rect': {'x': -3440, 'y': 0, 'width': 3440, 'height': 1440}}]
        self.tree = {'nodes': [
            {'type': 'workspace', 'name': 'trabajo', 'nodes': [
                {'id': 9, 'app_id': DESKTOP_ID}, {'id': 11, 'app_id': 'editor', 'window_properties': None},
                {'id': 12, 'window': 4, 'name': 'untrusted; exit', 'window_properties': {'class': 'Terminal'}}]},
            {'type': 'workspace', 'name': 'otro', 'nodes': [{'id': 99, 'app_id': 'browser'}]},
        ]}

    def test_only_selected_workspace_and_never_desktop(self):
        commands = plan(self.tree, self.workspaces, 'DP-1', LayoutOptions())
        self.assertEqual(len(commands), 2)
        self.assertTrue(commands[0].startswith('[con_id=11]'))
        self.assertIn('move absolute position -3428 px', commands[0])
        self.assertNotIn('untrusted', ''.join(commands))

    def test_disconnected_screen_does_not_fall_back(self):
        with self.assertRaises(ValueError):
            plan(self.tree, self.workspaces, 'DP-2', LayoutOptions())

    def test_no_commands_if_unreadable_geometry(self):
        self.workspaces[0]['rect']['width'] = 100
        with self.assertRaises(ValueError):
            plan(self.tree, self.workspaces, 'DP-1', LayoutOptions())

    def test_waits_for_client_and_reports_size_constraints(self):
        for shrink in (0, 7):
            with self.subTest(shrink=shrink):
                final = {'nodes': [{'id': identity, 'rect': dict(vars(box), width=box.width - shrink)}
                                   for identity, box in targets(self.tree, self.workspaces, 'DP-1', LayoutOptions())]}
                replies = [self.tree, self.workspaces, [{'success': True}], {'nodes': []}] + [final] * 5
                with patch('prosperus.window_session.request', side_effect=replies), \
                     patch('prosperus.window_session.time.sleep'):
                    result = apply('DP-1', LayoutOptions())
                self.assertEqual(result.count, 2)
                self.assertEqual(result.adjusted, 2 if shrink else 0)

    def test_accepted_command_is_not_success_if_window_exceeds_zone(self):
        final = {'nodes': [{'id': identity, 'rect': dict(vars(box), width=box.width + 100)}
                           for identity, box in targets(self.tree, self.workspaces, 'DP-1', LayoutOptions())]}
        with patch('prosperus.window_session.request', side_effect=[
                self.tree, self.workspaces, [{'success': True}], final]), \
             patch('prosperus.window_session.time.monotonic', side_effect=[0, 3]):
            with self.assertRaisesRegex(ValueError, 'Distribución incompleta'):
                apply('DP-1', LayoutOptions())

    def test_partial_command_failure_is_reported(self):
        with patch('prosperus.window_session.request', side_effect=[self.tree, self.workspaces,
                [{'success': True}, {'success': False, 'error': 'Ventana cerrada'}]]):
            with self.assertRaisesRegex(ValueError, 'Aplicación parcial: Ventana cerrada'):
                apply('DP-1', LayoutOptions())
