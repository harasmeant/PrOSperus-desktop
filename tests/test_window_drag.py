# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
import unittest
from unittest.mock import patch

from prosperus.window_drag import STILL, Drop, DragTracker, central_zone, joins_pattern, velocity
from prosperus.window_layouts import LayoutOptions
from prosperus.window_session import Arrangement, targets

AREA = (0, 0, 1920, 1080)


def frame(**rects):
    return {int(k[1:]): (r, AREA, 'DP-1') for k, r in rects.items()}


class TrackerTest(unittest.TestCase):
    def drag(self, path, step=0.04, size=(600, 400), con='w5'):
        """Arrastra la ventana por `path` y la deja quieta. Devuelve lo soltado."""
        tracker, t, drops = DragTracker(), 0.0, []
        tracker.feed(t, frame(**{con: (*path[0], *size)}))
        for point in path[1:]:
            t += step
            drops += tracker.feed(t, frame(**{con: (*point, *size)}))
        for _ in range(int(STILL / step) + 3):
            t += step
            drops += tracker.feed(t, frame(**{con: (*path[-1], *size)}))
        return drops, tracker

    def test_drag_then_still_is_a_drop(self):
        drops, tracker = self.drag([(0, 0), (40, 20), (80, 40), (120, 60)])
        self.assertEqual(len(drops), 1)
        self.assertEqual(drops[0].con_id, 5)
        self.assertEqual(drops[0].rect, (120, 60, 600, 400))
        self.assertAlmostEqual(drops[0].velocity[0], 1000, delta=1)
        self.assertFalse(tracker.active)

    def test_single_jump_is_not_a_drag(self):
        # Super+Mayús+flecha o una orden de IPC: un solo salto.
        drops, _ = self.drag([(0, 0), (900, 0)])
        self.assertEqual(drops, [])

    def test_resize_cancels(self):
        tracker = DragTracker()
        tracker.feed(0, frame(w5=(0, 0, 600, 400)))
        tracker.feed(.04, frame(w5=(10, 0, 600, 400)))
        tracker.feed(.08, frame(w5=(20, 0, 500, 400)))
        drops = [d for t in range(30) for d in tracker.feed(.1 + t * .04, frame(w5=(20, 0, 500, 400)))]
        self.assertEqual(drops, [])

    def test_pause_shorter_than_still_keeps_dragging(self):
        tracker = DragTracker()
        tracker.feed(0, frame(w5=(0, 0, 600, 400)))
        tracker.feed(.04, frame(w5=(10, 0, 600, 400)))
        tracker.feed(.08, frame(w5=(20, 0, 600, 400)))
        self.assertEqual(tracker.feed(.08 + STILL / 2, frame(w5=(20, 0, 600, 400))), [])
        self.assertTrue(tracker.active)

    def test_closed_window_is_forgotten(self):
        tracker = DragTracker()
        tracker.feed(0, frame(w5=(0, 0, 600, 400)))
        tracker.feed(.04, frame(w5=(10, 0, 600, 400)))
        self.assertEqual(tracker.feed(.08, {}), [])
        self.assertFalse(tracker.active)

    def test_velocity_uses_last_instants(self):
        samples = [(0, 0, 0), (1.0, 0, 0), (1.1, 100, 0), (1.15, 200, -50)]
        vx, vy = velocity(samples)
        self.assertAlmostEqual(vx, 200 / .15, delta=1)
        self.assertAlmostEqual(vy, -50 / .15, delta=1)


class DecisionTest(unittest.TestCase):
    def drop(self, x, y, v=(0, 0)):
        return Drop(5, (x - 300, y - 200, 600, 400), AREA, 'DP-1', v)  # centro en (x, y)

    def test_centre_joins(self):
        self.assertTrue(joins_pattern(self.drop(960, 540)))

    def test_corner_stays_loose(self):
        self.assertFalse(joins_pattern(self.drop(200, 150)))

    def test_flung_towards_centre_joins(self):
        # Soltada fuera pero yendo deprisa hacia el centro: por inercia llega.
        self.assertTrue(joins_pattern(self.drop(400, 540, v=(2000, 0))))
        self.assertFalse(joins_pattern(self.drop(400, 540, v=(-2000, 0))))

    def test_zone_is_centred(self):
        x, y, w, h = central_zone((100, 0, 1000, 500))
        self.assertEqual((x + w / 2, y + h / 2), (600, 250))


class ArrangementTest(unittest.TestCase):
    def setUp(self):
        self.tree = {'nodes': [{'type': 'workspace', 'name': 'A', 'floating_nodes': [
            {'id': i, 'type': 'floating_con', 'app_id': 'foot'} for i in (11, 12, 13)]}]}
        self.workspaces = [{'name': 'A', 'output': 'DP-1', 'visible': True,
                            'rect': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080}}]

    def ids(self, arrangement):
        return [i for i, _ in targets(self.tree, self.workspaces, 'DP-1', LayoutOptions(), arrangement)]

    def test_default_is_by_age(self):
        self.assertEqual(self.ids(Arrangement()), [11, 12, 13])

    def test_insert_last_takes_next_fibonacci_slot(self):
        arrangement = Arrangement().insert_last(11, [11, 12, 13])
        self.assertEqual(self.ids(arrangement), [12, 13, 11])
        boxes = dict(targets(self.tree, self.workspaces, 'DP-1', LayoutOptions(), arrangement))
        # La que estaba al final (13) se parte por la mitad para dejarle sitio a la nueva.
        self.assertEqual(boxes[13].width, boxes[11].width)
        self.assertEqual(boxes[13].x, boxes[11].x)

    def test_released_window_leaves_pattern_and_can_come_back(self):
        loose = Arrangement().release(12, [11, 12, 13])
        self.assertEqual(self.ids(loose), [11, 13])
        back = loose.insert_last(12, self.ids(loose))
        self.assertEqual(self.ids(back), [11, 13, 12])
        self.assertNotIn(12, back.loose)

    def test_new_windows_go_after_ordered_ones(self):
        self.assertEqual(self.ids(Arrangement((13, 11))), [13, 11, 12])


class ManagerDropTest(unittest.TestCase):
    def test_drop_in_centre_saves_order_and_arranges(self):
        from prosperus.window_manager import WindowManager
        tree = {'nodes': [{'type': 'workspace', 'name': 'A', 'floating_nodes': [
            {'id': i, 'type': 'floating_con', 'app_id': 'foot'} for i in (11, 12)]}]}
        workspaces = [{'name': 'A', 'output': 'DP-1', 'visible': True,
                       'rect': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080}}]
        manager = WindowManager()
        saved = []
        with patch('prosperus.window_manager.request', side_effect=[tree, workspaces]), \
             patch('prosperus.window_manager.load_arrangement', return_value=Arrangement()), \
             patch('prosperus.window_manager.save_arrangement', side_effect=lambda a, alive: saved.append(a)), \
             patch.object(manager, 'arrange') as arrange:
            manager._dropped(Drop(11, (660, 340, 600, 400), AREA, 'DP-1', (0, 0)))
        self.assertEqual(saved[0].order, (12, 11))
        arrange.assert_called_once_with(attempts=3, output='DP-1')

    def test_already_loose_window_moved_around_stays_put(self):
        from prosperus.window_manager import WindowManager
        manager = WindowManager()
        with patch('prosperus.window_manager.request', side_effect=[{'nodes': []}, []]), \
             patch('prosperus.window_manager.load_arrangement', return_value=Arrangement((), frozenset({11}))), \
             patch('prosperus.window_manager.save_arrangement') as save, \
             patch.object(manager, 'arrange') as arrange:
            manager._dropped(Drop(11, (0, 0, 600, 400), AREA, 'DP-1', (0, 0)))
        save.assert_not_called(); arrange.assert_not_called()

    def test_fullscreen_mode_ignores_drops(self):
        from prosperus.window_manager import WindowManager
        manager = WindowManager(); manager.mode = 'fullscreen'
        with patch('prosperus.window_manager.request') as request:
            manager._dropped(Drop(11, (660, 340, 600, 400), AREA, 'DP-1', (0, 0)))
        request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
