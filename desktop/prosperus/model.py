"""Project files, Markdown links, and explicit edits without an Obsidian dependency."""
# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import re
import os
import stat
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit


def searchable(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).casefold())
                   if unicodedata.category(c) != 'Mn')


class Vault:
    MAX_NOTE_BYTES = 2 * 1024 * 1024

    def __init__(self, root):
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError('El proyecto debe ser una carpeta.')

    def checked(self, path):
        path = Path(path)
        result = (path if path.is_absolute() else self.root / path).resolve(strict=True)
        if not result.is_relative_to(self.root):
            raise ValueError('La ruta queda fuera de la carpeta de proyectos.')
        if any(part.startswith('.') for part in result.relative_to(self.root).parts):
            raise ValueError('Las carpetas ocultas no forman parte de esta vista.')
        return result

    def entries(self, folder):
        folder = self.checked(folder)
        entries = []
        for candidate in folder.iterdir():
            if candidate.name.startswith('.'):
                continue
            try:
                path = self.checked(candidate)
                if path.is_dir() or path.suffix.lower() == '.md':
                    entries.append(path)
            except (OSError, ValueError):
                continue
        return sorted(set(entries), key=lambda p: (not p.is_dir(), searchable(p.name)))

    def notes(self, folder=None):
        # Do not follow directory symlinks or descend hidden directories.
        pending = [self.checked(folder or self.root)]
        seen = set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            for path in self.entries(current):
                if path.is_dir():
                    pending.append(path)
                else:
                    yield path

    def search(self, query, folder=None):
        terms = searchable(query).split()
        return [p for p in self.notes(folder) if all(t in searchable(p.relative_to(self.root)) for t in terms)]

    def read(self, path):
        path = self.checked(path)
        if path.suffix.lower() != '.md' or not path.is_file():
            raise ValueError('Esta vista admite notas Markdown (.md).')
        with path.open('rb') as handle:
            data = handle.read(self.MAX_NOTE_BYTES + 1)
        if len(data) > self.MAX_NOTE_BYTES:
            raise ValueError('La nota supera el límite de lectura de 2 MiB.')
        return data.decode('utf-8-sig')

    def child_path(self, folder, name, note=False):
        folder = self.checked(folder)
        name = name.strip()
        if not folder.is_dir():
            raise ValueError('El destino debe ser una carpeta.')
        if not name or name.startswith('.') or any(c in '/\\' or ord(c) < 32 for c in name):
            raise ValueError('Escribe un nombre sin rutas ni caracteres de control.')
        if note and not name.lower().endswith('.md'):
            name += '.md'
        path = folder / name
        if path.exists() or path.is_symlink():
            raise FileExistsError('Ya existe un elemento con ese nombre.')
        return path

    def create_note(self, folder, name):
        path = self.child_path(folder, name, note=True)
        with path.open('x', encoding='utf-8') as handle:
            handle.write('# ' + path.stem + '\n\n')
        return path

    def create_folder(self, folder, name):
        path = self.child_path(folder, name)
        path.mkdir()
        return path

    def save_note(self, path, text, expected):
        path = self.checked(path)
        if self.read(path) != expected:
            raise ValueError('La nota cambió fuera de esta ventana. Copia tus cambios antes de volver a abrirla; no se ha sobrescrito el archivo.')
        data = text.encode('utf-8')
        if len(data) > self.MAX_NOTE_BYTES:
            raise ValueError('La nota supera el límite de 2 MiB.')
        mode = stat.S_IMODE(path.stat().st_mode)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.prosperus-', delete=False) as handle:
                temporary = handle.name
                os.fchmod(handle.fileno(), mode)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            # Check again after preparing the replacement, before committing it.
            if self.read(path) != expected:
                raise ValueError('La nota cambió mientras se guardaba; el archivo no se ha sobrescrito.')
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def resolve_note(self, target, source):
        """Resolve relative Markdown links and unique wikilink names, within root."""
        source = self.checked(source)
        parsed = urlsplit(target)
        if parsed.scheme not in ('', 'file') or parsed.netloc:
            raise ValueError('Este lector no abre enlaces externos.')
        name = unquote(parsed.path)
        if not name:
            return source
        path = Path(name)
        if not path.suffix:
            path = path.with_suffix('.md')
        if path.suffix.lower() != '.md':
            raise ValueError('El enlace no apunta a una nota Markdown.')
        candidates = [path] if path.is_absolute() else [source.parent / path, self.root / path]
        for candidate in candidates:
            try:
                result = self.checked(candidate)
                if result.is_file():
                    return result
            except FileNotFoundError:
                continue
        if len(path.parts) == 1:
            matches = [p for p in self.notes() if p.name == path.name]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise ValueError('Hay varias notas con ese nombre; utiliza su ruta.')
        raise FileNotFoundError('No se encontró la nota enlazada.')

    def markdown(self, path):
        text = self.read(path)
        if text.startswith('---\n'):
            parts = text.split('\n---', 1)
            if len(parts) == 2:
                text = parts[1].lstrip('\r\n')
        # Preserve fenced and inline code; turn wikilinks into regular local links.
        from urllib.parse import quote
        def replace(match):
            target, _, label = match.group(1).partition('|')
            label = (label or target).replace('[', '\\[').replace(']', '\\]')
            return f'[{label}]({quote(target, safe="/#")})'
        chunks = re.split(r'(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`)', text)
        return ''.join(chunk if i % 2 else re.sub(r'\[\[([^\]\n]+)\]\]', replace, chunk)
                       for i, chunk in enumerate(chunks))
