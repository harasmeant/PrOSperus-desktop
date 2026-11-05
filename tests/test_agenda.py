import datetime
import tempfile
import unittest
from pathlib import Path

from prosperus import agenda

D = datetime.date


class AgendaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def note(self, relative, text=''):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def test_date_from_name_and_project_after_tareas(self):
        path = self.note('PrOSperus-desktop/notas/Tareas/Aspiradora/2026-11-06 - esquematizar habitación.md')
        task = agenda.task_for(path, self.root)
        self.assertEqual((task.day, task.title, task.project, task.done),
                         (D(2026, 11, 6), 'Esquematizar habitación', 'Aspiradora', False))

    def test_header_date_wins_over_name(self):
        path = self.note('DND/2026-11-09 - Reserva.md', '---\nestado: pendiente\nfecha_prevista: 2026-11-12\n---\n# Reserva\n')
        self.assertEqual(agenda.task_for(path, self.root).day, D(2026, 11, 12))

    def test_plain_fecha_is_when_written_not_a_task(self):
        path = self.note('PrOSperus-desktop/notas/21 - Seguimiento.md', '---\nfecha: 2026-10-29\n---\n')
        self.assertIsNone(agenda.task_for(path, self.root))

    def test_done_by_state_or_completion_date(self):
        a = self.note('X/2026-11-01 - a.md', '---\nestado: hecha\n---\n')
        b = self.note('X/2026-11-01 - b.md', '---\nestado: pendiente\nfecha_completada: 2026-11-02\n---\n')
        c = self.note('X/2026-11-01 - c.md', '---\nestado: pendiente\nfecha_completada:\n---\n')
        self.assertEqual([agenda.task_for(p, self.root).done for p in (a, b, c)], [True, True, False])

    def test_invalid_dates_and_unclosed_header_are_ignored(self):
        self.assertIsNone(agenda.task_for(self.note('X/2026-13-40 - mal.md'), self.root))
        path = self.note('X/nota.md', '---\nfecha_prevista: 2026-11-12\n# sin cerrar\n')
        self.assertIsNone(agenda.task_for(path, self.root))

    def test_program_material_is_skipped(self):
        keep = self.note('DND/Tareas/2026-11-09 - Reserva.md')
        skip = self.note('PrOSperus-desktop/demo/Escritorio/2026-11-09 - Ejemplo.md')
        hidden = self.note('.copias/2026-11-09 - Copia.md')
        found = agenda.tasks([keep, skip, hidden], self.root)
        self.assertEqual([t.path for t in found], [keep])

    def test_by_day_groups_pending_first(self):
        a = self.note('X/2026-11-01 - b.md', '---\nestado: hecha\n---\n')
        b = self.note('X/2026-11-01 - a.md')
        days = agenda.by_day(agenda.tasks([a, b], self.root))
        self.assertEqual([t.title for t in days[D(2026, 11, 1)]], ['A', 'B'])

    def test_new_task_note_round_trips(self):
        name = agenda.note_name(D(2026, 11, 20), '  Llamar  a la academia / cursos ')
        self.assertEqual(name, '2026-11-20 - Llamar a la academia - cursos.md')
        path = self.note('Cursos 3D/Tareas/' + name, agenda.note_text(D(2026, 11, 20), 'Llamar a la academia'))
        task = agenda.task_for(path, self.root)
        self.assertEqual((task.day, task.project, task.done), (D(2026, 11, 20), 'Cursos 3D', False))
        with self.assertRaises(ValueError):
            agenda.note_name(D(2026, 11, 20), ' / ')


class ClockTextTests(unittest.TestCase):
    def test_clock_and_headings_in_spanish(self):
        from prosperus.clock_calendar import clock_text, day_heading
        self.assertEqual(clock_text(datetime.datetime(2026, 11, 5, 9, 7)), '09:07  ·  jue 5 nov')
        today = D(2026, 11, 5)
        self.assertEqual(day_heading(today, today), 'Hoy, jueves 5 de noviembre')
        self.assertEqual(day_heading(D(2026, 11, 6), today), 'Mañana, viernes 6 de noviembre')
        self.assertEqual(day_heading(D(2026, 11, 20), today), 'Viernes 20 de noviembre')


if __name__ == '__main__':
    unittest.main()
