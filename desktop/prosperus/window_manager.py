# SPDX-License-Identifier: GPL-3.0-only
"""
Gestor de ventanas para el compositor Sway.

Mantiene una capa de ventanas flotantes sobre el escritorio,
organizando las aplicaciones mediante el protocolo IPC de Sway.
"""
import json
import os
import socket
import struct
import threading
import time
from PySide6.QtCore import QObject, Signal

from .window_session import request, walk, DESKTOP_ID, SHELL_IDS, apply
from .window_layouts import LayoutOptions
from .display_settings import primary_output

SUBSCRIBE_TYPE = 2
HEADER_SIZE = 14
MAX_SIZE = 8 * 1024 * 1024


# Lee datos de socket hasta tamaño exacto para IPC
def _exact(sock, size):
    # recv puede devolver menos bytes de los pedidos: leer hasta completar.
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise OSError('Sway cerró la conexión de eventos.')
        data.extend(chunk)
    return bytes(data)


def subscribe(events):
    """Suscribe a los eventos de Sway y genera cada mensaje recibido."""
    address = os.environ.get('SWAYSOCK')
    if not address:
        raise OSError('La variable SWAYSOCK no está definida.')
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(3)
        sock.connect(address)
        payload = json.dumps(events).encode()
        sock.sendall(b'i3-ipc' + struct.pack('=II', len(payload), SUBSCRIBE_TYPE) + payload)
        header = _exact(sock, HEADER_SIZE)
        if header[:6] != b'i3-ipc':
            raise OSError('Cabecera de respuesta inválida.')
        size, _ = struct.unpack('=II', header[6:])
        if size > MAX_SIZE:
            raise ValueError('Respuesta demasiado grande.')
        data = _exact(sock, size)
        reply = json.loads(data)
        if not reply.get('success'):
            raise OSError('Suscripción rechazada por Sway.')
        sock.settimeout(None)
        while True:
            header = _exact(sock, HEADER_SIZE)
            if header[:6] != b'i3-ipc':
                raise ValueError('Cabecera de evento inválida.')
            size, _ = struct.unpack('=II', header[6:])
            if size > MAX_SIZE:
                raise ValueError('Eventos demasiado grandes.')
            data = _exact(sock, size)
            yield json.loads(data)


def output_of(tree, con_id):
    """Pantalla (output de Sway) en la que está la ventana con_id, o None."""
    for output in tree.get('nodes', []):
        if output.get('type') == 'output' and any(n.get('id') == con_id for n in walk(output)):
            return output['name']
    return None


def other_outputs(outputs, main):
    """Pantallas activas distintas de la del escritorio, en el orden de Sway."""
    return [output['name'] for output in outputs if output['name'] != main and output.get('active')]


class WindowManager(QObject):
    windows_changed = Signal(list)
    message = Signal(str)
    project_step = Signal(int)
    # Super pulsada y soltada sola (Sway: bindsym --release Super_L).
    search_requested = Signal()
    # Alt+Tab / Alt+Mayús+Tab (nop prosperus-switch next|prev).
    switch_step = Signal(int)
    # Aplicación que acaba de recibir el foco: orden de «última usada» en Alt+Tab.
    focused = Signal(int)
    # Super+↓ / Super+↑ con el escritorio delante: minimizar / ampliar la nota enfocada.
    note_command = Signal(str)

    # Gestiona ventanas flotantes y organiza aplicaciones con IPC de Sway
    def __init__(self, parent=None, options_provider=None):
        super().__init__(parent)
        self.options_provider = options_provider or (lambda: LayoutOptions())
        self.mode = 'fibonacci'
        self.workspace = 'General'
        # Sway arranca en el espacio «1»: la primera vez siempre se mueve el escritorio.
        self._placed = False
        self.available = bool(os.environ.get('SWAYSOCK'))
        self._stopping = False
        # Última vez que se movió o cambió de tamaño una aplicación (ver _watch_geometry).
        self._moved_at = 0.0

    # Inicia hilo que gestiona ventanas flotantes en Sway
    def start(self):
        if not self.available:
            return
        self._stopping = False
        threading.Thread(target=self._run, daemon=True).start()
        threading.Thread(target=self._watch_geometry, daemon=True).start()

    def _watch_geometry(self):
        """Super+arrastrar mueve una ventana (y Super+clic derecho la redimensiona), pero al soltar
        Super Sway también lanza «Buscar»: no distingue el clic de ratón de «Super sola».
        Se apunta cuándo cambió la geometría de alguna aplicación para descartar esa búsqueda."""
        last = None
        while not self._stopping:
            try:
                rects = {n['id']: (n['rect']['x'], n['rect']['y'], n['rect']['width'], n['rect']['height'])
                         for n in walk(request(4)) if n.get('type') == 'floating_con'
                         and n.get('app_id') not in SHELL_IDS}
                if last is not None and any(last.get(i, r) != r for i, r in rects.items()):
                    self._moved_at = time.monotonic()
                last = rects
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(.25)

    def just_moved(self, within=1.5):
        return time.monotonic() - self._moved_at < within

    # Colocar escritorio en espacio de trabajo correcto
    def _place_desktop(self):
        # La orden de mover solo afecta a ventanas ya mapeadas: esperar a que
        # el escritorio exista en el árbol antes de llevarlo a su espacio.
        deadline = time.monotonic() + 20
        while not self._stopping and time.monotonic() < deadline:
            try:
                if any(n.get('app_id') == DESKTOP_ID for n in walk(request(4))):
                    self.switch_workspace(self.workspace)
                    if self._placed:
                        return
            except (OSError, ValueError):
                pass
            time.sleep(.2)
        self.message.emit('No se pudo colocar el escritorio en su espacio de trabajo.')

    # Mantener el escritorio organizado con eventos de Sway
    def _run(self):
        self._place_desktop()
        # Con la suscripción ya en marcha, para que la consola nueva se reparta al aparecer.
        threading.Timer(1.5, self._open_secondary).start()
        while not self._stopping:
            try:
                for event in subscribe(['window', 'binding']):
                    if self._stopping:
                        break
                    self._handle_event(event)
            except (OSError, ValueError) as e:
                self.message.emit(f'Conexión con Sway perdida, reintentando: {e}')
                threading.Event().wait(2)

    def _open_secondary(self):
        """Al arrancar, cada pantalla secundaria abre una consola sobre el fondo del proyecto
        (el mapa solo está en la principal); lo que se abra allí se reparte en Fibonacci."""
        if os.environ.get('PROSPERUS_NO_SECONDARY_TERMINAL'):
            return
        try:
            main = output_of(request(4), next((n['id'] for n in walk(request(4)) if n.get('app_id') == DESKTOP_ID
                                               and n.get('name') == 'PrOSperus desktop'), None))
            others = other_outputs(request(3), main)
            if not others or not main:
                return
            commands = []
            for i, name in enumerate(others):
                if '"' in name or '\\' in name:
                    continue
                # Regla en caliente: la consola marcada aparece directamente en su pantalla, sin
                # mover el foco (el escritorio sigue con el teclado).
                app_id = f'org.prosperus.Pantalla{i + 2}'
                commands += [f'for_window [app_id="{app_id}"] move container to output "{name}"',
                             f'exec /usr/bin/prosperus-terminal --app-id={app_id}']
            if commands:
                request(0, '; '.join(commands))
        except (OSError, ValueError, KeyError, StopIteration) as e:
            self.message.emit(f'No se pudo abrir la consola en la otra pantalla: {e}')

    # Gestiona ventanas y proyectos con eventos Sway
    def _handle_event(self, e):
        if 'binding' in e:
            cmd = e['binding'].get('command', '')
            if cmd.endswith('prosperus-project next'):
                self.project_step.emit(1)
                return
            elif cmd.endswith('prosperus-project prev'):
                self.project_step.emit(-1)
                return
            elif cmd.endswith('prosperus-search'):
                if not self.just_moved():
                    self.search_requested.emit()
                return
            elif cmd.endswith('prosperus-switch next') or cmd.endswith('prosperus-switch prev'):
                self.switch_step.emit(1 if cmd.endswith('next') else -1)
                return
            elif cmd.endswith('prosperus-windows minimize') or cmd.endswith('prosperus-windows maximize'):
                self.note_command.emit(cmd.rsplit(' ', 1)[1])
                return
        change = e.get('change')
        c = e.get('container', {})
        if c.get('app_id') in SHELL_IDS:
            return
        if (c.get('window_properties') or {}).get('class') == DESKTOP_ID:
            return
        if change == 'new':
            if c.get('type') == 'floating_con':
                return
            self.place(c['id'])
            self.refresh()
        elif change == 'close':
            if self.mode == 'fibonacci':
                self.arrange_all()
            self.refresh()
        elif change in ('title', 'move'):
            self.refresh()
        elif change == 'focus':
            self.focused.emit(c['id'])

    # Corrige tamaños iniciales de ventanas recién creadas
    def place(self, con_id):
        if self.mode == 'fullscreen':
            try:
                request(0, f'[con_id={con_id}] floating enable, fullscreen enable')
            except (OSError, ValueError) as e:
                self.message.emit(f'No se pudo ampliar la aplicación: {e}')
        else:
            # Recién creada, la ventana aún no ha hecho su primer dibujo y Sway le impone su
            # tamaño flotante por defecto: la primera orden de tamaño se pierde. Se reintenta.
            # Se organiza la pantalla donde ha aparecido, que puede no ser la enfocada.
            try:
                output = output_of(request(4), con_id)
            except (OSError, ValueError):
                output = None
            self.arrange(attempts=4, output=output)

    def arrange_all(self):
        """Todas las pantallas: al cerrar una ventana no se sabe ya en cuál estaba."""
        try:
            outputs = [o['name'] for o in request(3) if o.get('active')]
        except (OSError, ValueError, KeyError):
            outputs = [None]
        for output in outputs:
            self.arrange(output=output)

    # Organiza ventanas flotantes de una pantalla (por defecto, la enfocada)
    def arrange(self, attempts=1, output=None):
        for attempt in range(attempts):
            try:
                target = output or next(w['output'] for w in request(1) if w.get('focused'))
                apply(target, self.options_provider())
                return
            except ValueError as e:
                # Sin aplicaciones visibles no hay nada que organizar: no es un error.
                if 'No hay aplicaciones' in str(e):
                    return
                if attempt + 1 < attempts and 'incompleta' in str(e):
                    time.sleep(.25); continue
                self.message.emit(f'No se pudo organizar: {e}')
            except (OSError, KeyError, StopIteration) as e:
                self.message.emit(f'No se pudo organizar: {e}')
            return

    # Cambia el modo de colocación (pantalla completa o Fibonacci)
    def set_mode(self, mode):
        if mode not in ('fibonacci', 'fullscreen'):
            raise ValueError('Modo no válido')
        self.mode = mode
        if not self.available:
            return
        try:
            if mode == 'fullscreen':
                for n in walk(request(4)):
                    if n.get('focused') and n.get('app_id') != DESKTOP_ID and (n.get('app_id') or n.get('window')):
                        request(0, f'[con_id={n["id"]}] fullscreen enable')
                        break
            else:
                request(0, '[floating] fullscreen disable')
                self.arrange()
        except (OSError, ValueError) as e:
            self.message.emit(f'Error al cambiar modo: {e}')

    # Prepara nombres de ventanas para IPC eliminando caracteres especiales
    @staticmethod
    def _quoted(name):
        # Los nombres de carpeta llegan a órdenes de Sway: sin comillas ni barras.
        return '"' + name.replace('"', '').replace('\\', '') + '"'

    def _hidden(self):
        return self.workspace + ' · ocultas'

    def _windows(self):
        """Ventanas del proyecto actual: (nodo, oculta)."""
        found = []
        for ws in walk(request(4)):
            if ws.get('type') != 'workspace' or ws.get('name') not in (self.workspace, self._hidden()):
                continue
            for n in walk(ws):
                if (n.get('type') in ('con', 'floating_con') and (n.get('app_id') or n.get('window'))
                        and n.get('app_id') not in SHELL_IDS
                        and (n.get('window_properties') or {}).get('class') != DESKTOP_ID):
                    found.append((n, ws.get('name') == self._hidden()))
        return found

    # Actualiza lista de ventanas y emite cambios
    def refresh(self):
        try:
            windows = [{'id': n['id'], 'name': n.get('name') or n.get('app_id') or 'Aplicación', 'hidden': hidden}
                       for n, hidden in self._windows()]
            self.windows_changed.emit(windows)
        except (OSError, ValueError, KeyError):
            pass

    def switch_workspace(self, name):
        """Cada proyecto es un espacio de Sway; el escritorio viaja con él."""
        if not self.available or (self._placed and name == self.workspace):
            self.workspace = name; return
        self.workspace = name
        target = self._quoted(name)
        try:
            replies = request(0, f'[app_id="{DESKTOP_ID}"] move container to workspace {target}; workspace {target}')
            # Sin ventana que coincida, Sway cambiaría de espacio sin el escritorio.
            self._placed = all(reply.get('success') for reply in replies)
            if self._placed:
                self._keep_on_primary()
        except (OSError, ValueError) as e:
            self.message.emit(f'No se pudo cambiar de escritorio: {e}')
        self.refresh()

    def _keep_on_primary(self):
        """El proyecto se crea en la pantalla con el foco (al arrancar, la del portátil):
        se lleva a la principal elegida en Monitores, o a la externa si no hay ninguna."""
        primary = primary_output(request(3))
        current = next((w for w in request(1) if w.get('focused')), {})
        if primary and current.get('output') not in (None, primary) and '"' not in primary and '\\' not in primary:
            request(0, f'move workspace to output "{primary}"')

    def set_wallpaper(self, path, color):
        """Fondo de Sway (lo que se ve en las demás pantallas): el del proyecto actual.

        Solo se envía si cambia, porque cada orden vuelve a lanzar swaybg."""
        value = (str(path), 'fill') if path else (color, 'solid_color')
        if not self.available or value == getattr(self, '_wallpaper', None):
            return
        if '"' in value[0] or '\n' in value[0]:
            return  # no se puede citar con seguridad en una orden de Sway
        try:
            request(0, f'output * bg "{value[0]}" {value[1]}')
            self._wallpaper = value
        except (OSError, ValueError) as e:
            self.message.emit(f'No se pudo poner el fondo en las otras pantallas: {e}')

    # Enfocar ventana en workspace Sway
    def focus(self, con_id, hidden):
        try:
            if hidden:
                request(0, f'[con_id={con_id}] move container to workspace {self._quoted(self.workspace)}')
                self.place(con_id)
            request(0, f'[con_id={con_id}] focus')
        except (OSError, ValueError) as e:
            self.message.emit(f'No se pudo mostrar la aplicación: {e}')
        self.refresh()

    def focus_desktop(self):
        """Devuelve el foco al escritorio (para abrir una nota desde Alt+Tab)."""
        if self.available:
            try:
                request(0, f'[app_id="{DESKTOP_ID}" title="^PrOSperus desktop$"] focus')
            except (OSError, ValueError):
                pass

    def minimize(self, con_id):
        """Sway no implementa minimizar: se lleva la ventana al espacio de ocultas del proyecto."""
        try:
            request(0, f'[con_id={con_id}] move container to workspace {self._quoted(self._hidden())}')
        except (OSError, ValueError) as e:
            self.message.emit(f'No se pudo minimizar: {e}')
        self.refresh()

    def toggle(self, con_id, hidden):
        """Clic en la barra: recupera una ventana oculta, minimiza la enfocada y enfoca las demás."""
        try:
            focused = any(n['id'] == con_id and n.get('focused') for n in walk(request(4)))
        except (OSError, ValueError):
            focused = False
        if focused and not hidden:
            self.minimize(con_id)
        else:
            self.focus(con_id, hidden)

    def show_desktop(self):
        """Oculta las aplicaciones del proyecto actual para ver el mapa."""
        try:
            windows = self._windows()
            commands = [f'[con_id={n["id"]}] move container to workspace {self._quoted(self._hidden())}'
                        for n, hidden in windows if not hidden]
            if not commands:
                # Segunda pulsación: devolver las aplicaciones ocultas del proyecto.
                commands = [f'[con_id={n["id"]}] move container to workspace {self._quoted(self.workspace)}'
                            for n, hidden in windows if hidden]
                restore = True
            else:
                restore = False
            if commands:
                request(0, '; '.join(commands))
                if restore and self.mode == 'fibonacci':
                    self.arrange()
        except (OSError, ValueError) as e:
            self.message.emit(f'No se pudo mostrar el escritorio: {e}')
        self.refresh()

    def minimize_all(self):
        """Doble clic en el escritorio: oculta las aplicaciones visibles del proyecto (no las devuelve)."""
        try:
            visible = any(not hidden for _, hidden in self._windows())
        except (OSError, ValueError):
            return
        if visible:
            self.show_desktop()

    def stop(self):
        self._stopping = True


def main(argv=None):
    """Órdenes para atajos de Sway: actúan sobre el proyecto del espacio enfocado."""
    import sys
    args = sys.argv[1:] if argv is None else argv
    if args not in (['show-desktop'], ['minimize'], ['maximize']):
        print('Uso: prosperus-windows show-desktop|minimize|maximize', file=sys.stderr); return 2
    manager = WindowManager()
    try:
        if args == ['maximize']:
            from .window_handle import toggle_maximized
            toggle_maximized(); return 0
        current = next(w['name'] for w in request(1) if w.get('focused'))
        if args == ['minimize']:
            if current.endswith(' · ocultas'):
                return 0
            manager.workspace = current
            window = next((n for n in walk(request(4)) if n.get('focused') and n.get('type') in ('con', 'floating_con')
                           and n.get('app_id') != DESKTOP_ID), None)
            if window:
                manager.minimize(window['id'])
            return 0
    except (OSError, ValueError, KeyError, StopIteration) as error:
        print(error, file=sys.stderr); return 1
    # Desde el espacio de ocultas, el atajo devuelve las aplicaciones.
    if current.endswith(' · ocultas'):
        manager.workspace = current[:-len(' · ocultas')]
        request(0, 'workspace ' + manager._quoted(manager.workspace)); return 0
    manager.workspace = current
    manager.message.connect(lambda text: print(text, file=sys.stderr))
    manager.show_desktop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
