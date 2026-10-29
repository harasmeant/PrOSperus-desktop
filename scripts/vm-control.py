#!/usr/bin/env python3
"""Local development VM controls, via its Unix QMP socket."""
# SPDX-License-Identifier: GPL-3.0-only
import argparse
import json
from pathlib import Path
import socket


def command(name, arguments=None, iso=False):
    # Cada VM tiene su socket: las órdenes nunca deben llegar a otra sesión.
    directory = 'out/iso/vm' if iso else 'out/vm'
    path = Path(__file__).resolve().parents[1] / directory / 'qmp.sock'
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(10)
        connection.connect(str(path))
        stream = connection.makefile('rwb', buffering=0)
        json.loads(stream.readline())
        def execute(operation, args):
            stream.write(json.dumps({'execute': operation, 'arguments': args or {}}).encode() + b'\n')
            while True:
                response = json.loads(stream.readline())
                if 'error' in response:
                    raise RuntimeError(response['error'])
                if 'return' in response:
                    return response['return']
        execute('qmp_capabilities', {})
        return execute(name, arguments)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--iso', action='store_true', help='Control the Live ISO test VM.')
    parser.add_argument('action', choices=['status', 'screenshot', 'key', 'poweroff', 'quit'])
    parser.add_argument('value', nargs='?')
    args = parser.parse_args()
    if args.action == 'status':
        result = command('query-status', iso=args.iso)
    elif args.action == 'screenshot':
        filename = args.value or 'desktop.ppm'
        if Path(filename).name != filename or not filename.endswith('.ppm'):
            parser.error('Use a .ppm filename without a directory.')
        result = command('screendump', {'filename': '/output/screenshots/' + filename}, iso=args.iso)
    elif args.action == 'key':
        keys = (args.value or '').split('-')
        if not all(key.replace('_', '').isalnum() for key in keys):
            parser.error('Use QEMU key codes, e.g. ctrl-1 or esc.')
        result = command('send-key', {'keys': [{'type': 'qcode', 'data': key} for key in keys]}, iso=args.iso)
    else:
        result = command('system_powerdown' if args.action == 'poweroff' else 'quit', iso=args.iso)
    print(json.dumps(result))
