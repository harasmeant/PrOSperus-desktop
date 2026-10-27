"""Linux application catalogue and launching through the desktop's own API."""
import json
import os
import sys
import gi

gi.require_version('Gio', '2.0')
from gi.repository import Gio


def catalogue():
    return sorted([
        {'id': app.get_id(), 'name': app.get_display_name(),
         'description': app.get_description() or '',
         'keywords': list(app.get_keywords() or []) if hasattr(app, 'get_keywords') else []}
        for app in Gio.AppInfo.get_all() if app.get_id() and app.should_show()
    ], key=lambda app: app['name'].casefold())


def launch(desktop_id):
    app = next((app for app in Gio.AppInfo.get_all()
                if app.get_id() == desktop_id and app.should_show()), None)
    if app is None:
        raise ValueError('La aplicación ya no está instalada o está oculta.')
    # GUI processes must not inherit the JSON response pipe: their output could
    # corrupt the response or keep the launcher waiting until the app closes.
    sys.stdout.flush()
    sys.stderr.flush()
    saved = [os.dup(1), os.dup(2)]
    try:
        with open(os.devnull, 'w') as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            started = app.launch([], None)
    finally:
        for descriptor, original in zip((1, 2), saved):
            os.dup2(original, descriptor)
            os.close(original)
    if not started:
        raise RuntimeError('El sistema no ha podido iniciar la aplicación.')


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['list']:
            print(json.dumps(catalogue(), ensure_ascii=False))
        elif len(sys.argv) == 3 and sys.argv[1] == 'launch':
            launch(sys.argv[2])
            print('{}')
        else:
            raise ValueError('Acción no válida')
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
