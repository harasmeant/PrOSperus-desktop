# Gestión de ratón y teclado en VM / pantalla

## Selección técnica (autorizada)
- **Ratón:** `python-evdev` (captura eventos Linux a nivel `/dev/input/event*`; compatible con `virtio-mouse`).
- **Teclado:** `python-pynput` (monitor global + atajos sin depender de DE).

Ambos funcionan con `python3-pyside6` existente y mantienen independencia del DE.

## Qué resuelve
- Ratón invisible en QEMU/Boxes: `evdev` lee el stream del dispositivo; `pyside6` recibe eventos de `QMouseEvent`.
- Pantalla dividida / zoom: aparte de layout, falta selector (`xrandr` o Qt `QScreen`).
- Teclado: `pynput` permite capturar `Super`, `Ctrl+Espacio`, etc., sin conflictos con compositor Cage.

## Instalación recomendada (agregar a Containerfile.base)
```bash
RUN dnf -y --setopt=install_weak_deps=False install python3-evdev python3-pynput \
    && dnf clean all
```

## Uso básico (referencia para desktop)
```python
# Ratón (evdev) — leer dispositivo en VM
from evdev import InputDevice, categorize, ecodes

# Teclado (pynput) — captura global
from pynput import keyboard

def on_press(key):
    # Manejo de F1, Ctrl+Espacio, etc.
    pass

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
```

## Pendiente inmediato
- [ ] Añadir `python3-evdev` y `python3-pynput` a `image/Containerfile.base` o `Containerfile`
- [ ] Verificar que `virtio-mouse` y `virtio-keyboard` estén presentes en `dracut --add-drivers`
- [ ] Añadir selector de resolución (`xrandr` o Qt) a la UI para corregir división/zoom
