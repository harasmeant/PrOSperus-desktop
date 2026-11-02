"""Píldora de controles sobre la aplicación enfocada (Sway no dibuja botones de ventana).

Proceso propio con app_id org.prosperus.Handle: Sway lo deja flotante, fijo en todos
los espacios y sin foco al aparecer (ver /etc/sway/prosperus.conf). Sigue a la ventana
enfocada consultando el árbol de Sway y actúa por con_id, nunca por título.
"""
# SPDX-License-Identifier: GPL-3.0-only
import sys

from .window_session import DESKTOP_ID, HANDLE_ID, request, walk

HIDDEN_SUFFIX = ' · ocultas'


def find_target(tree, previous=None):
    """(ventana, espacio) enfocados que admiten controles, o la anterior si el foco está en la píldora.

    Se ignoran el escritorio, la propia píldora, los espacios de ocultas y las ventanas
    a pantalla completa (taparían la píldora).
    """
    candidates = {}
    focused = None
    for ws in walk(tree):
        if ws.get('type') != 'workspace' or ws.get('name', '').startswith('__'):
            continue
        for n in walk(ws):
            if n.get('type') not in ('con', 'floating_con') or not (n.get('app_id') or n.get('window')):
                continue
            ident = n.get('app_id') or (n.get('window_properties') or {}).get('class')
            if ident == HANDLE_ID and n.get('focused'):
                focused = 'handle'
            if ident in (DESKTOP_ID, HANDLE_ID) or ws['name'].endswith(HIDDEN_SUFFIX) or n.get('fullscreen_mode'):
                continue
            candidates[n['id']] = (n, ws)
            if n.get('focused'):
                focused = n['id']
    if focused == 'handle':
        focused = previous
    return candidates.get(focused, (None, None))


def handle_position(rect, width):
    """Centrada sobre el borde superior de la ventana, sin tapar sus propios botones."""
    return rect['x'] + (rect['width'] - width) // 2, rect['y'] + 2


def maximize_commands(node, workspace, saved):
    """Alterna entre ocupar el espacio de trabajo y la geometría guardada en `saved`."""
    ident = node['id']
    if ident in saved:
        r = saved.pop(ident)
    else:
        saved[ident] = dict(node['rect'])
        r = workspace['rect']
    return (f'[con_id={ident}] floating enable, resize set width {r["width"]} px height {r["height"]} px, '
            f'move absolute position {r["x"]} px {r["y"]} px, focus')


def minimize_command(node, workspace):
    name = (workspace['name'] + HIDDEN_SUFFIX).replace('"', '').replace('\\', '')
    return f'[con_id={node["id"]}] move container to workspace "{name}"'


def main():
    from PySide6.QtCore import QRectF, Qt, QTimer
    from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
    from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget
    from .window_controls import HoverControls

    QGuiApplication.setDesktopFileName(HANDLE_ID)
    app = QApplication(sys.argv)

    class Handle(QWidget):
        def __init__(self):
            super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setWindowTitle('Controles de ventana')
            layout = QHBoxLayout(self); layout.setContentsMargins(8, 3, 8, 3)
            self.controls = HoverControls(self, watch=self)
            self.controls.triggered.connect(self.trigger)
            self.controls.animation.valueChanged.connect(self.update)
            layout.addWidget(self.controls)
            self.setFixedSize(self.sizeHint())
            self.target = self.workspace = None
            self.position = None
            self.saved = {}
            self.timer = QTimer(self, interval=250, timeout=self.follow); self.timer.start()

        def paintEvent(self, event):
            p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            alpha = 90 + int(140 * self.controls.progress)
            rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
            border = QColor(255, 255, 255, 18 + int(30 * self.controls.progress))
            p.setPen(QPen(border, 1)); p.setBrush(QColor(20, 24, 20, alpha))
            p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        def follow(self):
            try:
                node, ws = find_target(request(4), self.target and self.target['id'])
            except (OSError, ValueError):
                return
            self.target, self.workspace = node, ws
            self.controls.set_maximized(node is not None and node['id'] in self.saved)
            if node is None:
                self.position = None; self.hide(); return
            if not self.isVisible():
                self.show()
            position = handle_position(node['rect'], self.width())
            if position != self.position:
                try:
                    replies = request(0, f'[app_id="{HANDLE_ID}"] move absolute position {position[0]} px {position[1]} px')
                    # Recién mostrada, Sway aún no la ha mapeado y la orden no coincide con nada:
                    # solo se da por colocada cuando Sway lo confirma (se reintenta en el siguiente ciclo).
                    if replies and all(r.get('success') for r in replies):
                        self.position = position
                except (OSError, ValueError):
                    pass

        def trigger(self, action):
            if self.target is None:
                return
            if action == 'close':
                command = f'[con_id={self.target["id"]}] kill'
                self.saved.pop(self.target['id'], None)
            elif action == 'minimize':
                command = minimize_command(self.target, self.workspace)
            else:
                command = maximize_commands(self.target, self.workspace, self.saved)
            try:
                request(0, command)
            except (OSError, ValueError):
                pass
            self.follow()

    handle = Handle()
    handle.follow()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
