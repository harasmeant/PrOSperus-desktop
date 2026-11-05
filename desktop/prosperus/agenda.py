# SPDX-License-Identifier: GPL-3.0-only
"""Tareas con fecha sacadas de las notas, para el calendario del reloj.

No hay base de datos aparte: la fecha sale de la propia nota. Primero de la cabecera
(`fecha_prevista`, `inicio_previsto` o `fecha_revision`; `fecha` a secas es cuándo se escribió, no cuenta) y, si no la tiene, del
nombre del archivo cuando empieza por AAAA-MM-DD («2026-11-06 - Esquematizar habitación.md»).
Una nota está hecha si su `estado` lo dice o si tiene `fecha_completada`."""
import datetime
import re
from dataclasses import dataclass
from pathlib import Path

FIELDS = ('fecha_prevista', 'inicio_previsto', 'fecha_revision')
DONE = {'hecha', 'hecho', 'completada', 'completado', 'terminada', 'terminado', 'cerrada', 'cerrado', 'hecha ✓'}
NAME_DATE = re.compile(r'^(\d{4})-(\d{2})-(\d{2})(?:\s*[-·–—]\s*|\s+|$)(.*)$')
FIELD_DATE = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
# Material de programas (demos, pruebas, copias): no son tareas tuyas aunque lleven fecha en el nombre.
SKIP = {'node_modules', '__pycache__', '.venv', 'venv', 'out', 'evidence', 'prototype', 'demo',
        'demo-system', 'graphify-out', 'tests', 'site-packages'}
HEAD_BYTES = 4096


@dataclass(frozen=True)
class Task:
    path: Path
    day: datetime.date
    title: str
    project: str
    done: bool


def _date(year, month, day):
    try:
        return datetime.date(int(year), int(month), int(day))
    except ValueError:
        return None


def front_matter(text):
    """Claves sencillas «clave: valor» de la cabecera --- … ---; lo demás se ignora."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == '---':
            return fields
        key, sep, value = line.partition(':')
        if sep and key and not key[0].isspace():
            fields[key.strip().lower()] = value.strip().strip('"\'')
    return {}  # cabecera sin cerrar: no se fía


def task_for(path, root):
    """La tarea de una nota, o None si la nota no tiene fecha."""
    path = Path(path)
    match = NAME_DATE.match(path.stem)
    named = _date(*match.groups()[:3]) if match else None
    try:
        with path.open('r', encoding='utf-8', errors='replace') as handle:
            head = handle.read(HEAD_BYTES)
    except OSError:
        head = ''
    fields = front_matter(head)
    day = None
    for key in FIELDS:
        found = FIELD_DATE.search(fields.get(key, ''))
        if found:
            day = _date(*found.groups())
            if day:
                break
    day = day or named
    if day is None:
        return None
    title = (match.group(4).strip() if match else '') or path.stem
    status = fields.get('estado', '').lower()
    done = status in DONE or bool(FIELD_DATE.search(fields.get('fecha_completada', '')))
    return Task(path, day, title[:1].upper() + title[1:], project_of(path, root), done)


def project_of(path, root):
    """Dentro de una carpeta Tareas/, la carpeta que sigue (Tareas/Aspiradora/… → Aspiradora);
    si no, la carpeta de primer nivel. Vacío para notas sueltas en la raíz."""
    try:
        folders = Path(path).relative_to(root).parts[:-1]
    except ValueError:
        return ''
    lowered = [part.lower() for part in folders]
    if 'tareas' in lowered:
        index = len(lowered) - 1 - lowered[::-1].index('tareas')
        if index + 1 < len(folders):
            return folders[index + 1]
    return folders[0] if folders else ''


def skipped(path, root):
    try:
        parts = Path(path).relative_to(root).parts[:-1]
    except ValueError:
        return True
    return any(part in SKIP or part.startswith('.') for part in parts)


def tasks(notes, root):
    """Tareas de una lista de notas (la del índice de la bóveda), por fecha y título."""
    found = []
    for note in notes:
        if skipped(note, root):
            continue
        task = task_for(note, root)
        if task:
            found.append(task)
    return sorted(found, key=lambda t: (t.day, t.done, t.project.lower(), t.title.lower()))


def by_day(found):
    days = {}
    for task in found:
        days.setdefault(task.day, []).append(task)
    return days


def note_text(day, title):
    """Nota nueva de tarea con el mismo formato que las de Tareas/."""
    return (f'---\ntipo: tarea\nestado: pendiente\nfecha_prevista: {day.isoformat()}\nfecha_completada:\n'
            f'tags: [tarea]\n---\n\n# {title}\n\n- [ ] \n')


def note_name(day, title):
    clean = ' '.join(title.replace('/', '-').replace('\\', '-').split()).strip(' .-')
    if not clean:
        raise ValueError('Escribe un título para la tarea.')
    return f'{day.isoformat()} - {clean}.md'
