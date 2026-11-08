# SPDX-License-Identifier: GPL-3.0-only
"""Linux application catalogue and launching through the desktop's own API."""
import json
import os
import sys
import gi

gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib


# Lista aplicaciones instaladas y visibles, ordenadas por nombre.
def catalogue():
    return sorted([
        {'id': app.get_id(), 'name': app.get_display_name(),
         'description': app.get_description() or '',
         'keywords': list(app.get_keywords() or []) if hasattr(app, 'get_keywords') else [],
         'icon': (app.get_icon().to_string() if app.get_icon() else '')
        }
        for app in Gio.AppInfo.get_all() if app.get_id() and app.should_show()
    ], key=lambda app: app['name'].casefold())


# Ejecuta un callable con stdout y stderr redirigidos a /dev/null.
def _without_output(start):
    # GUI processes must not inherit the JSON response pipe: their output could
    # corrupt the response or keep the launcher waiting until the app closes.
    sys.stdout.flush()
    sys.stderr.flush()
    saved = [os.dup(1), os.dup(2)]
    try:
        with open(os.devnull, 'w') as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            return start()
    finally:
        for descriptor, original in zip((1, 2), saved):
            os.dup2(original, descriptor)
            os.close(original)


def _app_entry(app):
    return {'id': app.get_id(), 'name': app.get_display_name(),
            'icon': app.get_icon().to_string() if app.get_icon() else ''}


def apps_for(path):
    """Programas para elegir: primero los que dicen abrir este tipo, luego todos los demás."""
    content_type = Gio.content_type_guess(path, None)[0]
    seen, apps = set(), []
    suggested = Gio.AppInfo.get_all_for_type(content_type) if content_type else []
    rest = sorted(Gio.AppInfo.get_all(), key=lambda a: a.get_display_name().casefold())
    for group, items in (('suggested', suggested), ('other', rest)):
        for app in items:
            if app.get_id() and app.get_id() not in seen and app.should_show():
                seen.add(app.get_id())
                apps.append(dict(_app_entry(app), group=group))
    return {'choose': apps, 'path': path, 'type': content_type or '',
            'type_name': Gio.content_type_get_description(content_type) if content_type else ''}


# Abre un archivo con la aplicación predeterminada; si no hay, devuelve la lista para preguntar.
def open_file(path):
    """Abre con la predeterminada o devuelve {'choose': [...]} para que el escritorio pregunte."""
    file = Gio.File.new_for_path(path)
    if not file.query_exists(None):
        raise ValueError('El archivo ya no existe.')
    content_type = Gio.content_type_guess(path, None)[0]
    default = Gio.AppInfo.get_default_for_type(content_type, False) if content_type else None
    if default is None or not _without_output(lambda: default.launch([file], None)):
        return apps_for(path)
    return {}


def open_with(desktop_id, path, remember=False):
    """Abre el archivo con el programa elegido; con remember, queda como predeterminado de ese tipo."""
    app = next((a for a in Gio.AppInfo.get_all() if a.get_id() == desktop_id), None)
    if app is None:
        raise ValueError('La aplicación ya no está instalada.')
    file = Gio.File.new_for_path(path)
    if not file.query_exists(None):
        raise ValueError('El archivo ya no existe.')
    if remember:
        content_type = Gio.content_type_guess(path, None)[0]
        if content_type:
            try:
                app.set_as_default_for_type(content_type)
            except GLib.Error:
                pass  # abrir es lo importante; recordar es un extra
    if not _without_output(lambda: app.launch([file], None)):
        raise RuntimeError('El sistema no ha podido iniciar ' + app.get_display_name() + '.')


# Lanza una aplicación de escritorio por su ID de archivo .desktop.
def launch(desktop_id):
    app = next((app for app in Gio.AppInfo.get_all()
                if app.get_id() == desktop_id and app.should_show()), None)
    if app is None:
        raise ValueError('La aplicación ya no está instalada o está oculta.')
    if not _without_output(lambda: app.launch([], None)):
        raise RuntimeError('El sistema no ha podido iniciar la aplicación.')


# Punto de entrada CLI: list, launch, open u open_with.
if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['list']:
            print(json.dumps(catalogue(), ensure_ascii=False))
        elif len(sys.argv) == 3 and sys.argv[1] == 'launch':
            launch(sys.argv[2])
            print('{}')
        elif len(sys.argv) == 3 and sys.argv[1] == 'open':
            print(json.dumps(open_file(sys.argv[2]), ensure_ascii=False))
        elif len(sys.argv) == 3 and sys.argv[1] == 'choose':
            print(json.dumps(apps_for(sys.argv[2]), ensure_ascii=False))
        elif len(sys.argv) in (4, 5) and sys.argv[1] == 'open_with':
            open_with(sys.argv[2], sys.argv[3], sys.argv[4:] == ['remember'])
            print('{}')
        else:
            raise ValueError('Acción no válida')
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
