# SPDX-License-Identifier: GPL-3.0-only
"""Archivos clasificados por proyecto: lo que llega a la carpeta de entrada (descargas) pasa a
<proyecto>/<tipo> (Imágenes, Documentos…), creando la carpeta del tipo solo con el primer archivo.

Las extensiones desconocidas se preguntan una vez y la respuesta vale para todos los proyectos
(~/.config/prosperus/destinos.json). extension, folder_for y unique_target las escribió
qwen2.5-coder (local), correctas a la primera."""
import json
import os
import shutil
from pathlib import Path

KINDS = {
    'Imágenes': ('png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'avif', 'heic', 'bmp', 'tif', 'tiff', 'ico'),
    'Documentos': ('pdf', 'doc', 'docx', 'odt', 'rtf', 'txt', 'md', 'xls', 'xlsx', 'ods', 'csv',
                   'ppt', 'pptx', 'odp', 'epub'),
    'Vídeos': ('mp4', 'mkv', 'webm', 'mov', 'avi', 'm4v'),
    'Audio': ('mp3', 'flac', 'ogg', 'oga', 'opus', 'wav', 'm4a', 'aac'),
    'Comprimidos': ('zip', '7z', 'rar', 'tar', 'gz', 'xz', 'bz2', 'zst', 'tgz', 'tar.gz', 'tar.xz',
                    'tar.zst', 'tar.bz2'),
}
# Descargas a medias de navegadores (Firefox/Zen, Chromium) y temporales: se esperan.
PARTIAL = ('.part', '.crdownload', '.download', '.tmp', '.partial')


def incoming_dir():
    """Carpeta de entrada: XDG_DOWNLOAD_DIR de la sesión apunta aquí (prosperus-session)."""
    return Path.home() / '.local' / 'share' / 'prosperus' / 'entrantes'


def memory_path():
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'prosperus' / 'destinos.json'


def load_memory(path=None):
    """Destinos recordados por extensión: {'stl': 'Modelos 3D'}. Vacío si no hay o no se lee."""
    try:
        data = json.loads(Path(path or memory_path()).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str) and safe_folder(v)} \
        if isinstance(data, dict) else {}


def save_memory(memory, path=None):
    path = Path(path or memory_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(memory, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    tmp.replace(path)


def safe_folder(name):
    """Nombre de carpeta de tipo válido: una sola carpeta, sin rutas ni ocultas."""
    name = (name or '').strip()
    return bool(name) and '/' not in name and not name.startswith('.') and name not in ('.', '..')


def is_partial(name):
    """Descarga sin terminar u oculta: no se mueve todavía."""
    lower = name.lower()
    return name.startswith('.') or lower.endswith(PARTIAL)


def extension(name):
    """Lowercase extension without the dot. Double extensions: 'a.tar.gz' -> 'tar.gz', 'a.tar.xz' -> 'tar.xz',
    'a.tar.zst' -> 'tar.zst', 'a.tar.bz2' -> 'tar.bz2'. 'Foto.JPG' -> 'jpg'. No extension ('README') -> ''."""
    lower = name.lower()
    for ext in ('tar.gz', 'tar.xz', 'tar.zst', 'tar.bz2'):
        if lower.endswith('.' + ext):
            return ext
    if '.' not in name or name.startswith('.') and name.count('.') == 1:
        return ''
    return lower.rsplit('.', 1)[1]

def folder_for(name, remembered):
    """Type folder for a file name: first the user's remembered choice (dict extension -> folder name),
    then KINDS. None if unknown."""
    ext = extension(name)
    if not ext:
        return None
    if ext in remembered:
        return remembered[ext]
    for folder, extensions in KINDS.items():
        if ext in extensions:
            return folder
    return None

def unique_target(directory, name):
    """Path in directory that does not exist yet: 'Foto.png', then 'Foto (2).png', 'Foto (3).png'...
    Keeps double extensions: 'a.tar.gz' -> 'a (2).tar.gz'."""
    directory = Path(directory)
    target = directory / name
    if not target.exists():
        return target
    ext = extension(name)
    stem = name[:-(len(ext) + 1)] if ext else name
    suffix = '.' + ext if ext else ''
    n = 2
    while True:
        candidate = directory / f'{stem} ({n}){suffix}'
        if not candidate.exists():
            return candidate
        n += 1


def project_root(vault_root, folder):
    """Proyecto (carpeta de primer nivel) al que pertenece `folder`; None en «Tus proyectos»."""
    vault_root, folder = Path(vault_root), Path(folder)
    try:
        parts = folder.relative_to(vault_root).parts
    except ValueError:
        return None
    return vault_root / parts[0] if parts else None


def route(path, project, memory):
    """Mueve un archivo a <project>/<carpeta de su tipo>. Devuelve el destino, o None si el tipo
    es desconocido (hay que preguntar). La carpeta del tipo se crea aquí, con el primer archivo."""
    path = Path(path)
    folder = folder_for(path.name, memory)
    if folder is None:
        return None
    return move_to(path, Path(project) / folder)


def move_to(path, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = unique_target(directory, Path(path).name)
    shutil.move(str(path), str(target))
    return target


def type_folders(project):
    """Carpetas de tipo que se pueden elegir: las conocidas y las que ya hay en el proyecto."""
    names = list(KINDS) + ['Capturas']
    try:
        names += sorted(p.name for p in Path(project).iterdir() if p.is_dir() and safe_folder(p.name))
    except OSError:
        pass
    return list(dict.fromkeys(names))
