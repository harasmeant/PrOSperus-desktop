# Mouse / keyboard input handling using evdev + pynput
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

def get_mouse_device():
    if not HAS_EVDEV:
        return None
    for path in os.listdir('/dev/input'):
        if path.startswith('event'):
            try:
                dev = InputDevice(f'/dev/input/{path}')
                if ecodes.EV_REL in dev.capabilities():
                    return dev
            except Exception:
                continue
    return None

def listen_keyboard(on_press=None):
    if not HAS_PYNPUT or on_press is None:
        return
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
