"""Adaptador experimental para organizar aplicaciones reales mediante Sway IPC.

Solo actúa al solicitarlo: no instala un compositor ni modifica su configuración.
Usa IDs numéricos del árbol, nunca títulos de ventanas como órdenes ejecutables.
"""
# SPDX-License-Identifier: GPL-3.0-only
import argparse
from dataclasses import dataclass
import json
import os
import socket
import struct
import time
from .window_layouts import LayoutOptions, Rect, arrange

DESKTOP_ID = 'org.prosperus.Desktop'


@dataclass(frozen=True)
class AppliedLayout:
    count: int
    adjusted: int


def request(kind, payload=''):
    def receive(connection, size):
        data = bytearray()
        while len(data) < size:
            chunk = connection.recv(size - len(data))
            if not chunk:
                raise OSError('La sesión cerró la conexión.')
            data.extend(chunk)
        return data

    address = os.environ.get('SWAYSOCK')
    if not address:
        raise OSError('La sesión actual todavía no permite organizar aplicaciones externas.')
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(3)
        connection.connect(address)
        data = payload.encode()
        connection.sendall(b'i3-ipc' + struct.pack('=II', len(data), kind) + data)
        header = receive(connection, 14)
        size, reply_kind = struct.unpack('=II', header[6:])
        if header[:6] != b'i3-ipc' or reply_kind != kind or size > 8 * 1024 * 1024:
            raise ValueError('Respuesta del compositor no válida.')
        return json.loads(receive(connection, size))


def walk(node):
    yield node
    for child in node.get('nodes', []) + node.get('floating_nodes', []):
        yield from walk(child)


def targets(tree, workspaces, output, options):
    # El monitor elegido debe tener un espacio visible. Nunca caer al monitor
    # enfocado si se desconectó el solicitado: podría mover ventanas ajenas.
    workspace = next((w for w in workspaces if w.get('visible') and w.get('output') == output), None)
    if workspace is None:
        raise ValueError('La pantalla seleccionada ya no tiene un espacio visible.')
    node = next((n for n in walk(tree) if n.get('type') == 'workspace' and n.get('name') == workspace['name']), None)
    if node is None:
        raise ValueError('El espacio de trabajo ha cambiado; vuelve a intentarlo.')
    windows = [n for n in walk(node) if (n.get('app_id') or n.get('window'))
               and n.get('app_id') != DESKTOP_ID
               and (n.get('window_properties') or {}).get('class') != DESKTOP_ID]
    windows.sort(key=lambda n: n['id'])
    if not windows:
        raise ValueError('No hay aplicaciones que organizar en esta pantalla.')
    area = Rect(**workspace['rect'])
    boxes = arrange(area, len(windows), options)
    return [(int(window['id']), box) for window, box in zip(windows, boxes)]


def commands_for(placements):
    commands = []
    for identity, box in placements:
        # px son coordenadas lógicas en el compositor. Los orígenes negativos de
        # una pantalla situada a la izquierda también son válidos.
        commands.append(f'[con_id={identity}] fullscreen disable, floating enable, '
                        f'resize set width {box.width} px height {box.height} px, '
                        f'move absolute position {box.x} px {box.y} px')
    return commands


def plan(tree, workspaces, output, options):
    return commands_for(targets(tree, workspaces, output, options))


def apply(output, options):
    placements = targets(request(4), request(1), output, options)
    commands = commands_for(placements)
    # Validar todas las geometrías antes de enviar la primera orden. Sway no
    # ofrece transacciones: un cierre de ventana durante la operación se informa.
    responses = request(0, '; '.join(commands))
    errors = [r.get('error', 'Orden rechazada') for r in responses if not r.get('success')]
    if errors:
        raise ValueError('Aplicación parcial: ' + '; '.join(errors))
    # Aceptar la orden no garantiza el tamaño: una aplicación puede imponer
    # mínimos y Wayland confirma la nueva geometría de forma asíncrona.
    deadline = time.monotonic() + 2
    previous, stable = None, 0
    while True:
        actual = {n.get('id'): n.get('rect') for n in walk(request(4))}
        observed = [actual.get(identity) for identity, _ in placements]
        stable = stable + 1 if observed == previous else 0
        previous = observed
        # Un terminal puede redondear hacia abajo al tamaño de sus caracteres.
        # Se acepta si conserva el origen, cabe en su zona y sigue siendo legible.
        fits = all(rect is not None and rect['x'] == box.x and rect['y'] == box.y
                   and 320 <= rect['width'] <= box.width and 220 <= rect['height'] <= box.height
                   for rect, (_, box) in zip(observed, placements))
        if fits and stable >= 4:
            adjusted = sum(rect != vars(box) for rect, (_, box) in zip(observed, placements))
            return AppliedLayout(len(commands), adjusted)
        if time.monotonic() >= deadline:
            raise ValueError('Distribución incompleta: una ventana se cerró o no aceptó el tamaño. '
                             'Revisa las ventanas antes de volver a organizar.')
        time.sleep(.05)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--mode', default='spiral')
    parser.add_argument('--gap', type=int, default=12)
    parser.add_argument('--ratio', type=int, default=50)
    parser.add_argument('--max-width', type=int, default=0)
    args = parser.parse_args()
    try:
        result = apply(args.output, LayoutOptions(args.mode, args.gap, args.ratio, args.max_width))
        message = f'{result.count} aplicaciones organizadas.'
        if result.adjusted:
            message += f' {result.adjusted} ajustaron su tamaño dentro de la zona asignada.'
        print(message)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
