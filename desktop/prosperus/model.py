"""Project files, Markdown links, and explicit edits without an Obsidian dependency."""
# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import json
import re
import os
import stat
import tempfile
import unicodedata
from urllib.parse import quote, unquote, urlsplit


# Búsquedas insensibles a mayúsculas y acentos
def searchable(value):
    # Normalizar consulta y texto del mismo modo permite buscar sin tildes ni
    # distinguir mayúsculas, conservando intacto el contenido de los archivos.
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).casefold())
                   if unicodedata.category(c) != 'Mn')


ORIGINS = '.origen.json'  # dentro de .papelera: de dónde venía cada elemento


# Escrito por qwen2.5-coder (local) con dos correcciones: prefijo de carpeta y sufijo .md.
WIKILINK = re.compile(r'\[\[([^\]\n|#]+)((?:#[^\]\n|]*)?)((?:\|[^\]\n]*)?)\]\]')
# group(1) = target (may contain folders, may end in .md), group(2) = '#heading' or '', group(3) = '|label' or ''

def rename_wikilinks(text, old, new):
    """Point wikilinks to note `old` at `new`. Returns (new_text, count)."""
    count = 0

    def replace(match):
        nonlocal count
        target, heading, label = match.group(1), match.group(2), match.group(3)
        # Split target into folder prefix and name at the LAST '/' (prefix keeps its trailing '/', may be '').
        cut = target.rfind('/') + 1
        prefix, name = target[:cut], target[cut:]
        # If name (stripped) ends with '.md' (case-insensitive), remove it and remember suffix = the original 4 chars, else suffix = ''.
        suffix = name[-3:] if name.lower().endswith('.md') else ''
        name = name[:-3] if suffix else name
        # If name.strip().casefold() != old.strip().casefold(): return match.group(0) unchanged.
        if name.strip().casefold() != old.strip().casefold():
            return match.group(0)
        # Count += 1 and return '[[' + prefix + new + suffix + heading + label + ']]'
        count += 1
        return f'[[{prefix}{new}{suffix}{heading}{label}]]'

    chunks = re.split(r'(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`)', text)
    # Apply WIKILINK.sub(replace, chunk) ONLY to chunks with an EVEN index (index 0, 2, 4...); keep odd (code) chunks unchanged.
    new_chunks = [WIKILINK.sub(replace, chunk) if i % 2 == 0 else chunk for i, chunk in enumerate(chunks)]
    return ''.join(new_chunks), count


# Borrador de qwen2.5-coder; corregido (lo aplicaba dentro del código) y ampliado a carpetas.
MDLINK = re.compile(r'(\[[^\]\n]*\]\()(<[^>\n]+>|[^)\s]+)((?:\s+"[^"\n]*")?\))')
# group(1) = '[label](' ; group(2) = destination, maybe wrapped in <...>, maybe URL-encoded (%20) ; group(3) = optional title and ')'

def rename_markdown_links(text, note_dir, old_path, new_path):
    """Rewrite relative Markdown links (also links into a renamed folder) in a note located in folder `note_dir` that point to `old_path`
    so they point to `new_path`. All three are absolute path strings. Returns (new_text, count)."""
    count = 0

    def replace(match):
        nonlocal count
        head, dest, tail = match.group(1), match.group(2), match.group(3)
        wrapped = dest.startswith('<') and dest.endswith('>')
        raw = dest[1:-1] if wrapped else dest
        if '://' in raw or raw.startswith('mailto:') or raw.startswith('#'):
            return match.group(0)
        path_part, sep, fragment = raw.partition('#')
        target = os.path.normpath(os.path.join(note_dir, unquote(path_part)))
        old = os.path.normpath(old_path)
        if target == old:
            moved = new_path
        elif target.startswith(old + os.sep):  # carpeta renombrada: enlaces a lo que hay dentro
            moved = os.path.normpath(new_path) + target[len(old):]
        else:
            return match.group(0)
        rel = os.path.relpath(moved, note_dir).replace(os.sep, '/')
        if wrapped:
            new_dest = '<' + rel + sep + fragment + '>'
        else:
            new_dest = quote(rel, safe='/') + sep + fragment
        count += 1
        return head + new_dest + tail

    # Do not touch code: apply MDLINK.sub only to even chunks of
    # re.split(r'(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`)', text)
    chunks = re.split(r'(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`)', text)
    for i in range(0, len(chunks), 2):
        chunks[i] = MDLINK.sub(replace, chunks[i])
    return (''.join(chunks), count)



def is_wallpaper_name(stem):
    """wallpaper y wallpaper-07 (fondos por horas) son configuración, no documentos."""
    stem = stem.lower()
    return stem == 'wallpaper' or (stem.startswith('wallpaper-') and stem[10:].isdigit())

class Vault:
    MAX_NOTE_BYTES = 2 * 1024 * 1024

    # Valida que el proyecto sea una carpeta válida
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError('El proyecto debe ser una carpeta.')

    # Valida rutas dentro de proyectos sin carpetas ocultas
    def checked(self, path):
        path = Path(path)
        result = (path if path.is_absolute() else self.root / path).resolve(strict=True)
        if not result.is_relative_to(self.root):
            raise ValueError('La ruta queda fuera de la carpeta de proyectos.')
        if any(part.startswith('.') for part in result.relative_to(self.root).parts):
            raise ValueError('Las carpetas ocultas no forman parte de esta vista.')
        return result

    # Lista archivos visibles no carpetas ni wallpapers
    def entries(self, folder):
        folder = self.checked(folder)
        entries = []
        for candidate in folder.iterdir():
            if candidate.name.startswith('.'):
                continue
            try:
                path = self.checked(candidate)
                # El fondo de la carpeta es configuración, no un documento del mapa.
                if path.is_dir() or not is_wallpaper_name(path.stem):
                    entries.append(path)
            except (OSError, ValueError):
                continue
        return sorted(set(entries), key=lambda p: (not p.is_dir(), searchable(p.name)))

    def notes(self, folder=None):
        return (path for path in self.files(folder) if path.suffix.lower() == '.md')

    # Listar archivos sin ocultos ni enlaces
    def files(self, folder=None):
        # Do not follow directory symlinks or descend hidden directories.
        pending = [self.checked(folder or self.root)]
        seen = set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            try:
                entries = self.entries(current)
            except (OSError, ValueError):
                # A missing/unreadable branch must not hide other search results.
                continue
            for path in entries:
                if path.is_dir():
                    pending.append(path)
                else:
                    yield path

    def search(self, query, folder=None):
        """Match every term across a note's relative path and saved Markdown.

        Name matches come first. Unreadable/oversized notes can still match by
        name, and never prevent searching the remaining files. Read one note
        at a time without keeping a second copy of the vault in memory.
        """
        terms = searchable(query).split()
        by_name, by_content = [], []
        for path in self.files(folder):
            name = searchable(path.relative_to(self.root))
            missing = [term for term in terms if term not in name]
            if not missing:
                by_name.append(path)
                continue
            if path.suffix.lower() != '.md':
                continue  # Otros archivos solo coinciden por nombre.
            try:
                content = searchable(self.read(path))
            except (OSError, ValueError, UnicodeError):
                continue
            if all(term in content for term in missing):
                by_content.append(path)
        return by_name + by_content

    def search_projects(self, query):
        """Find project covers by name or by matching notes inside them."""
        # El resultado es la portada del proyecto, aunque la coincidencia esté
        # en una nota de varios niveles más abajo (p. ej. «impresora» en Cursos 3D).
        terms = searchable(query).split()
        return [path for path in self.entries(self.root) if path.is_dir() and
                (all(term in searchable(path.name) for term in terms) or self.search(query, path))]

    # Lee notas Markdown hasta 2 MiB
    def read(self, path):
        path = self.checked(path)
        if path.suffix.lower() != '.md' or not path.is_file():
            raise ValueError('Esta vista admite notas Markdown (.md).')
        with path.open('rb') as handle:
            data = handle.read(self.MAX_NOTE_BYTES + 1)
        if len(data) > self.MAX_NOTE_BYTES:
            raise ValueError('La nota supera el límite de lectura de 2 MiB.')
        return data.decode('utf-8-sig')

    # Valida rutas únicas y válidas
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

    # Crear notas con título automático
    def create_note(self, folder, name):
        path = self.child_path(folder, name, note=True)
        with path.open('x', encoding='utf-8') as handle:
            handle.write('# ' + path.stem + '\n\n')
        return path

    # Crea carpetas para proyectos
    def create_folder(self, folder, name):
        path = self.child_path(folder, name)
        path.mkdir()
        return path

    def folders(self):
        """Todas las carpetas visibles, la raíz primero; destinos para crear o mover."""
        found = [self.root]
        for current, names, _ in os.walk(self.root):
            names[:] = sorted((n for n in names if not n.startswith('.')), key=str.lower)
            found += [Path(current) / n for n in names]
        return sorted(found, key=lambda p: str(p.relative_to(self.root)).lower() if p != self.root else '')

    def move(self, path, folder):
        """Mueve una nota o carpeta a otra carpeta conservando el nombre; nunca sobrescribe."""
        path, folder = self.checked(path), self.checked(folder)
        if path == self.root:
            raise ValueError('No se puede mover la carpeta de proyectos.')
        if not folder.is_dir():
            raise ValueError('El destino debe ser una carpeta.')
        if path.parent == folder:
            raise ValueError('Ya está en esa carpeta.')
        if folder.is_relative_to(path):
            raise ValueError('No se puede mover una carpeta dentro de sí misma.')
        target = folder / path.name
        if target.exists() or target.is_symlink():
            raise FileExistsError('Ya existe un elemento con ese nombre en el destino.')
        # Mismo sistema de archivos: rename es atómico y no deja copias a medias.
        os.rename(path, target)
        return target

    TRASH = '.papelera'

    def rename(self, path, name):
        """Renombra una nota o carpeta en su sitio. Al renombrar una nota, los wikilinks que la
        nombran se actualizan en todas las notas. Devuelve (nueva ruta, notas actualizadas)."""
        path = self.checked(path)
        if path == self.root:
            raise ValueError('No se puede renombrar la carpeta de proyectos.')
        note = path.is_file()
        if note and path.suffix.lower() != '.md':
            raise ValueError('Solo se renombran notas Markdown y carpetas.')
        target = self.child_path(path.parent, name, note=note)
        os.rename(path, target)
        updated = []
        for other in list(self.notes()):
            try:
                text = self.read(other)
                changed, count = rename_markdown_links(text, str(other.parent), str(path), str(target))
                if note and target.stem.casefold() != path.stem.casefold():
                    changed, more = rename_wikilinks(changed, path.stem, target.stem)
                    count += more
                if count:
                    self.save_note(other, changed, text); updated.append(other)
            except (OSError, ValueError):
                continue  # una nota ilegible no impide renombrar
        return target, updated

    def trash(self, path):
        """Mueve a .papelera (oculta, en la raíz) sin borrar nada; nunca sobrescribe."""
        path = self.checked(path)
        bin_ = self.root / self.TRASH
        if path == self.root or path == bin_ or path.is_relative_to(bin_):
            raise ValueError('Esto no se puede mover a la papelera.')
        bin_.mkdir(exist_ok=True)
        target, number = bin_ / path.name, 2
        while target.exists() or target.is_symlink():
            target = bin_ / f'{path.stem} ({number}){path.suffix}'; number += 1
        os.rename(path, target)
        # Se recuerda de dónde venía para poder devolverlo a su sitio.
        origins = self._origins()
        origins[target.name] = str(path.relative_to(self.root))
        self._save_origins(origins)
        return target

    # Obtiene orígenes almacenados en JSON
    def _origins(self):
        try:
            data = json.loads((self.root / self.TRASH / ORIGINS).read_text(encoding='utf-8'))
            return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    # Guardar orígenes en JSON seguro
    def _save_origins(self, origins):
        file = self.root / self.TRASH / ORIGINS
        temporary = file.with_name(ORIGINS + '.tmp')
        temporary.write_text(json.dumps(origins, ensure_ascii=False, indent=1), encoding='utf-8')
        temporary.replace(file)

    def trashed(self):
        """Elementos de la papelera: [(ruta en la papelera, ruta original relativa o None)], recientes primero."""
        bin_ = self.root / self.TRASH
        if not bin_.is_dir():
            return []
        origins = self._origins()
        items = [p for p in bin_.iterdir() if p.name != ORIGINS and not p.name.startswith(ORIGINS) and not p.is_symlink()]
        items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [(p, origins.get(p.name)) for p in items]

    def restore(self, name):
        """Devuelve un elemento de la papelera a su carpeta (o a la raíz si ya no existe); nunca sobrescribe."""
        bin_ = self.root / self.TRASH
        item = bin_ / Path(name).name
        if not item.exists() or item.is_symlink() or item.name.startswith(ORIGINS):
            raise FileNotFoundError('Ya no está en la papelera.')
        origins = self._origins()
        original = origins.get(item.name)
        folder = self.root
        if original:
            candidate = (self.root / original).parent
            if candidate.is_dir() and candidate.resolve().is_relative_to(self.root) and not candidate.resolve().is_relative_to(bin_):
                folder = candidate.resolve()
        base = Path(original).name if original else item.name
        stem, suffix = (Path(base).stem, Path(base).suffix) if item.is_file() else (base, '')
        target, number = folder / base, 2
        while target.exists() or target.is_symlink():
            target = folder / f'{stem} ({number}){suffix}'; number += 1
        os.rename(item, target)
        origins.pop(item.name, None)
        self._save_origins(origins)
        return target

    # Evitar sobrescribir archivos modificados al guardar
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

    # Convertir enlaces wikilink a enlaces normales en Markdown
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

    def links(self, path):
        """Notas a las que enlaza `path` (wikilinks y enlaces Markdown locales)."""
        # shortcut: un wikilink por nombre recorre todas las notas; añadir índice si la bóveda crece.
        text = self.read(path)
        chunks = re.split(r'(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`)', text)
        targets = set()
        for chunk in chunks[::2]:
            found = re.findall(r'\[\[([^\]\n|#]+)', chunk) + re.findall(r'\]\(([^)\s#]+)', chunk)
            for target in found:
                target = target.strip()
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                    continue  # enlace con esquema: no es una nota local
                try:
                    resolved = self.resolve_note(target, path)
                except (OSError, ValueError):
                    continue
                if resolved != path:
                    targets.add(resolved)
        return targets
