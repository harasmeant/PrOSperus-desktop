# Mouse / keyboard: non-blocking for Qt desktop
# SPDX-License-Identifier: GPL-3.0-only
import os

try:
    from evdev import InputDevice, ecodes
    HAS_EVDEV = True
except Exception:
    HAS_EVDEV = False

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except Exception:
    HAS_PYNPUT = False

# Busca un dispositivo de entrada que informe eventos de movimiento relativo (EV_REL).
def get_mouse_device():
    if not HAS_EVDEV:
        return None
    try:
        for path in os.listdir('/dev/input'):
            if path.startswith('event'):
                dev = InputDevice(f'/dev/input/{path}')
                if ecodes.EV_REL in dev.capabilities():
                    return dev
    except Exception:
        pass
    return None

# Inicia un listener global de teclado en hilo daemon; pynput falla en Wayland puro (Sway/Cage), por lo que el escritorio gestiona sus atajos mediante Qt.
def listen_keyboard(on_press=None):
    """Start a global key listener in a daemon thread and return it.

    pynput runs its own thread, so the Qt main loop is never blocked.
    Under pure Wayland (Cage/Sway) pynput cannot see global keys; the
    desktop keeps handling its shortcuts through Qt (desktop_keys.py).
    Returns None when pynput is unavailable or no callback is given.
    """
    if not HAS_PYNPUT or on_press is None:
        return None
    try:
        listener = keyboard.Listener(on_press=on_press, daemon=True)
        listener.start()
        return listener
    except Exception:
        return None
