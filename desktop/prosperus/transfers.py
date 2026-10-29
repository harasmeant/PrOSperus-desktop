"""Copy selected local items without overwriting or following symbolic links."""
# SPDX-License-Identifier: GPL-3.0-only
import os
from pathlib import Path
import shutil
import stat


def validate_source(path):
    path = Path(path).expanduser().absolute()
    if path.is_symlink():
        raise ValueError('No se copian enlaces simbólicos: ' + path.name)
    mode = path.lstat().st_mode
    if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise ValueError('Solo se pueden copiar archivos normales y carpetas: ' + path.name)
    if path.is_dir():
        for directory, folders, files in os.walk(path, followlinks=False):
            for name in folders + files:
                candidate = Path(directory) / name
                mode = candidate.lstat().st_mode
                if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                    raise ValueError('La carpeta contiene un enlace o archivo especial: ' + str(candidate.relative_to(path)))
    return path.resolve(strict=True)


def available_name(folder, source, directory=False):
    name = source.name
    candidate = folder / name
    suffix = '' if directory else source.suffix
    stem = name if directory or not suffix else name[:-len(suffix)]
    number = 1
    while candidate.exists() or candidate.is_symlink():
        ending = ' - copia' if number == 1 else f' - copia {number}'
        candidate = folder / (stem + ending + suffix)
        number += 1
    return candidate


def copy_to_handle(source, outgoing):
    # O_NOFOLLOW also checks a source replaced with a symlink after preflight.
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as incoming:
        mode = os.fstat(incoming.fileno()).st_mode
        if not stat.S_ISREG(mode):
            raise ValueError('El origen ya no es un archivo normal.')
        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
        os.fchmod(outgoing.fileno(), stat.S_IMODE(mode) & 0o777)


def copy_file(source, destination):
    with destination.open('xb') as outgoing:
        copy_to_handle(source, outgoing)


def copy_tree(source, destination):
    if source.is_symlink():
        raise ValueError('La carpeta de origen se ha convertido en un enlace.')
    for child in source.iterdir():
        if child.is_symlink():
            raise ValueError('No se copian enlaces simbólicos: ' + child.name)
        target = destination / child.name
        if child.is_dir():
            target.mkdir()
            copy_tree(child, target)
        else:
            copy_file(child, target)


def copy_into(vault, sources, folder):
    """Copies a batch; a failure removes only destinations created by this batch."""
    folder = vault.checked(folder)
    if not folder.is_dir():
        raise ValueError('El destino debe ser una carpeta.')
    sources = [validate_source(p) for p in dict.fromkeys(map(Path, sources))]
    if not sources:
        raise ValueError('No hay archivos o carpetas seleccionados.')
    for source in sources:
        if source.is_dir() and folder.is_relative_to(source):
            raise ValueError('No se puede copiar una carpeta dentro de sí misma.')
        if source.name.startswith('.'):
            raise ValueError('Selecciona una carpeta o archivo visible.')
    # Selecting a parent and its child means one copy of the parent, not two.
    sources = [p for p in sources if not any(p != other and p.is_relative_to(other) for other in sources)]
    created = []
    # Registrar solo destinos que hemos creado: si falla el lote, la limpieza
    # puede retirarlos sin borrar archivos previos ni modificar los originales.
    try:
        for source in sources:
            is_directory = source.is_dir()
            target = available_name(folder, source, is_directory)
            if is_directory:
                target.mkdir()
                created.append(target)
                copy_tree(source, target)
            else:
                # Reserve this name before adding it to the rollback set.
                with target.open('xb') as outgoing:
                    created.append(target)
                    copy_to_handle(source, outgoing)
        return created
    except Exception:
        for target in reversed(created):
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)
        raise
