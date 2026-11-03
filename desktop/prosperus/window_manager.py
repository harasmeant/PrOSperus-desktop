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

from .window_session import request, walk, DESKTOP_ID, HANDLE_ID, apply
from .window_layouts import LayoutOptions

SUBSCRIBE_TYPE = 2
HEADER_SIZE = 14
MAX_SIZE = 8 * 1024 * 1024


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


class WindowManager(QObject):
    windows_changed = Signal(list)
    message = Signal(str)
    project_step = Signal(int)

    def __init__(self, parent=None, options_provider=None):
        super().__init__(parent)
        self.options_provider = options_provider or (lambda: LayoutOptions())
        self.mode = 'fibonacci'
        self.workspace = 'General'
        # Sway arranca en el espacio «1»: la primera vez siempre se mueve el escritorio.
        self._placed = False
        self.available = bool(os.environ.get('SWAYSOCK'))
        self._stopping = False

    def start(self):
        if not self.available:
            return
        self._stopping = False
        threading.Thread(target=self._run, daemon=True).start()

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

    def _run(self):
        self._place_desktop()
        while not self._stopping:
            try:
                for event in subscribe(['window', 'binding']):
                    if self._stopping:
                        break
                    self._handle_event(event)
            except (OSError, ValueError) as e:
                self.message.emit(f'Conexión con Sway perdida, reintentando: {e}')
                threading.Event().wait(2)

    def _handle_event(self, e):
        if 'binding' in e:
            cmd = e['binding'].get('command', '')
            if cmd.endswith('prosperus-project next'):
                self.project_step.emit(1)
                return
            elif cmd.endswith('prosperus-project prev'):
                self.project_step.emit(-1)
                return
        change = e.get('change')
        c = e.get('container', {})
        if c.get('app_id') in (DESKTOP_ID, HANDLE_ID):
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
                self.arrange()
            self.refresh()
        elif change in ('title', 'move'):
            self.refresh()

    def place(self, con_id):
        if self.mode == 'fullscreen':
            try:
                request(0, f'[con_id={con_id}] floating enable, fullscreen enable')
            except (OSError, ValueError) as e:
                self.message.emit(f'No se pudo ampliar la aplicación: {e}')
        else:
            # Recién creada, la ventana aún no ha hecho su primer dibujo y Sway le impone su
            # tamaño flotante por defecto: la primera orden de tamaño se pierde. Se reintenta.
            self.arrange(attempts=4)

    def arrange(self, attempts=1):
        for attempt in range(attempts):
            try:
                focused_output = next(w['output'] for w in request(1) if w.get('focused'))
                apply(focused_output, self.options_provider())
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
                        and n.get('app_id') not in (DESKTOP_ID, HANDLE_ID)
                        and (n.get('window_properties') or {}).get('class') != DESKTOP_ID):
                    found.append((n, ws.get('name') == self._hidden()))
        return found

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
        except (OSError, ValueError) as e:
            self.message.emit(f'No se pudo cambiar de escritorio: {e}')
        self.refresh()

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

    def focus(self, con_id, hidden):
        try:
            if hidden:
                request(0, f'[con_id={con_id}] move container to workspace {self._quoted(self.workspace)}')
                self.place(con_id)
            request(0, f'[con_id={con_id}] focus')
        except (OSError, ValueError) as e:
            self.message.emit(f'No se pudo mostrar la aplicación: {e}')
        self.refresh()

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

    def stop(self):
        self._stopping = True


def main(argv=None):
    """Órdenes para atajos de Sway: actúan sobre el proyecto del espacio enfocado."""
    import sys
    args = sys.argv[1:] if argv is None else argv
    if args not in (['show-desktop'], ['minimize']):
        print('Uso: prosperus-windows show-desktop|minimize', file=sys.stderr); return 2
    manager = WindowManager()
    try:
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
