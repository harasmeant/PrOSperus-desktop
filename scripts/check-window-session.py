#!/usr/bin/env python3
"""Prueba Sway con pantallas virtuales y terminales desechables, sin GPU del host.

Ejecutar con el contenedor window-tests, PYTHONPATH=/source/desktop y /output
escribible. El finally detiene exclusivamente los procesos creados aquí.
"""
# SPDX-License-Identifier: GPL-3.0-only
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from prosperus.window_layouts import LayoutOptions, Rect, arrange
from prosperus.window_session import apply, request, walk


def wait_for(check, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(.1)
    raise RuntimeError('Timeout esperando al compositor o a una ventana de prueba.')


with tempfile.TemporaryDirectory(prefix='prosperus-sway-') as runtime:
    runtime = Path(runtime)
    config = runtime / 'config'
    config.write_text('''output HEADLESS-1 mode 3440x1440 position 0 0
output HEADLESS-2 mode 1920x1080 position 3440 0
workspace 1 output HEADLESS-1
workspace 2 output HEADLESS-2
default_border pixel 2
focus_follows_mouse no
seat seat0 fallback true
''')
    env = os.environ.copy()
    for key in ('SWAYSOCK', 'WAYLAND_DISPLAY', 'DISPLAY'):
        env.pop(key, None)
    env.update(XDG_RUNTIME_DIR=str(runtime), WLR_BACKENDS='headless',
               WLR_RENDERER='pixman', WLR_HEADLESS_OUTPUTS='2', WLR_LIBINPUT_NO_DEVICES='1')
    children = []
    with Path('/output/sway.log').open('w') as log:
        sway = subprocess.Popen(['sway', '-c', str(config)], env=env, stdout=log, stderr=log)
        try:
            address = wait_for(lambda: next(runtime.glob('sway-ipc.*.sock'), None))
            env['SWAYSOCK'] = str(address); os.environ['SWAYSOCK'] = str(address)
            display = wait_for(lambda: next((p for p in runtime.glob('wayland-*') if p.is_socket()), None))
            env['WAYLAND_DISPLAY'] = display.name

            def terminal(identity, workspace, constrained=False):
                request(0, f'workspace {workspace}')
                child = subprocess.Popen(['foot', '--app-id=' + identity,
                    '--override=resize-by-cells=' + ('yes' if constrained else 'no'), 'sh', '-c',
                    'printf "PrOSperus — ventana de prueba\\n"; sleep 180'], env=env, stdout=log, stderr=log)
                children.append(child)
                return wait_for(lambda: next((n for n in walk(request(4)) if n.get('app_id') == identity), None))

            for index in range(4):
                terminal(f'prosperus-test-{index}', 1)
            other = terminal('prosperus-other-screen', 2)
            # El nodo aparece antes de que el cliente confirme su primer tamaño.
            # Esperar a esa confirmación evita comparar contra el rectángulo inicial.
            last, stable = None, 0
            def settled():
                global last, stable
                current = {n['id']: n['rect'] for n in walk(request(4)) if n.get('app_id')}
                stable = stable + 1 if current == last else 0
                last = current
                return stable >= 3 and current[other['id']]['width'] > 0
            wait_for(settled)
            before = last[other['id']]
            outputs = request(3)
            assert len([o for o in outputs if o.get('active')]) == 2
            results = []
            for mode in ('spiral', 'columns', 'centered'):
                options = LayoutOptions(mode, 12, 50)
                result = apply('HEADLESS-1', options)
                assert result.count == 4 and result.adjusted == 0
                workspace = next(w for w in request(1) if w['name'] == '1')
                expected = arrange(Rect(**workspace['rect']), 4, options)
                def matches():
                    nodes = {n.get('app_id'): n for n in walk(request(4)) if n.get('app_id')}
                    for i, rect in enumerate(expected):
                        actual = nodes[f'prosperus-test-{i}']['rect']
                        if actual != vars(rect):
                            return False
                    return nodes['prosperus-other-screen']['rect'] == before
                try:
                    wait_for(matches)
                except RuntimeError:
                    Path('/output/geometry-error.json').write_text(json.dumps({
                        'mode': mode, 'expected': [vars(r) for r in expected],
                        'actual': [{'app_id': n.get('app_id'), 'rect': n['rect']}
                                   for n in walk(request(4)) if n.get('app_id')],
                        'other_before': before}, indent=2))
                    raise
                subprocess.run(['grim', '-o', 'HEADLESS-1', f'/output/{mode}-3440.png'], env=env, check=True)
                results.append({'mode': mode, 'windows': 4, 'exact_geometry': True, 'other_output_unchanged': True})
            # La otra pantalla prueba un cliente que redondea a celdas: debe
            # permanecer dentro de su zona y avisar del tamaño ajustado.
            terminal('prosperus-constrained', 2, constrained=True)
            constrained = apply('HEADLESS-2', LayoutOptions())
            assert constrained.count == 2 and constrained.adjusted == 1
            results.append({'cell_size_constraints_reported': True})
            Path('/output/verification.json').write_text(json.dumps(results, indent=2) + '\n')
            # Captura de los controles Qt sobre Wayland real, con configuración
            # temporal: no escribe preferencias ni abre proyectos del usuario.
            request(0, 'workspace 1')
            preview_env = dict(env, QT_QPA_PLATFORM='wayland', XDG_CONFIG_HOME=str(runtime / 'settings'))
            subprocess.run(['python3', '-c', '''
from pathlib import Path
import tempfile
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication
from prosperus.shell import Desktop, STYLE
from prosperus.layout_settings import LayoutDialog
app = QApplication([])
app.setDesktopFileName('org.prosperus.Desktop')
app.setStyleSheet(STYLE)
with tempfile.TemporaryDirectory() as root:
    shell = Desktop(Path(root)); shell.show()
    def open_controls():
        dialog = LayoutDialog(shell, QSettings(root + '/settings.ini', QSettings.Format.IniFormat))
        def capture():
            assert dialog.selected_screen().name() == 'HEADLESS-1'
            assert dialog.profile.currentData() == 'ultrawide'
            assert dialog.grab().save('/output/layout-settings.png')
            dialog.reject()
        QTimer.singleShot(1000, capture)
        dialog.exec()
        shell.close(); app.quit()
    QTimer.singleShot(400, open_controls)
    app.exec()
'''], env=preview_env, stdout=log, stderr=log, check=True, timeout=15)
            print('SWAY_LAYOUTS_OK: 4 aplicaciones, 3 distribuciones, 2 pantallas aisladas.')
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
            if sway.poll() is None:
                sway.terminate()
            for child in children + [sway]:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait()
