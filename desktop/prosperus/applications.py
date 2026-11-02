# SPDX-License-Identifier: GPL-3.0-only
"""Linux application catalogue and launching through the desktop's own API."""
import json
import os
import sys
import gi

gi.require_version('Gio', '2.0')
from gi.repository import Gio


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


# Abre un archivo con la aplicación predeterminada del escritorio.
def open_file(path):
    """Abre un archivo con la aplicación predeterminada del sistema."""
    file = Gio.File.new_for_path(path)
    if not file.query_exists(None):
        raise ValueError('El archivo ya no existe.')
    if not _without_output(lambda: Gio.AppInfo.launch_default_for_uri(file.get_uri(), None)):
        raise RuntimeError('No hay ninguna aplicación para abrir este archivo.')


# Lanza una aplicación de escritorio por su ID de archivo .desktop.
def launch(desktop_id):
    app = next((app for app in Gio.AppInfo.get_all()
                if app.get_id() == desktop_id and app.should_show()), None)
    if app is None:
        raise ValueError('La aplicación ya no está instalada o está oculta.')
    if not _without_output(lambda: app.launch([], None)):
        raise RuntimeError('El sistema no ha podido iniciar la aplicación.')


# Punto de entrada CLI: list, launch o open.
if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['list']:
            print(json.dumps(catalogue(), ensure_ascii=False))
        elif len(sys.argv) == 3 and sys.argv[1] == 'launch':
            launch(sys.argv[2])
            print('{}')
        elif len(sys.argv) == 3 and sys.argv[1] == 'open':
            open_file(sys.argv[2])
            print('{}')
        else:
            raise ValueError('Acción no válida')
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
