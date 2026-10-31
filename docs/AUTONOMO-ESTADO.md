# Estado de trabajo autónomo

Fecha: 31-10-2026
Estado: procediendo sin parar (autorizado por usuario).

Seleccionado:
- `python3-evdev` para ratón (VM + captura eventos)
- `python3-pynput` para teclado (atajos globales)
- `image/Containerfile.base` actualizado con ambos paquetes
- `docs/ARQUITECTURA-DISTRO.md` actualizado con referencia

Siguiente paso lógico (si el usuario confirma o sigue sin parar):
- Aplicar en `desktop/prosperus/desktop_keys.py` o crear módulo de captura (`mouse_capture.py`, `keyboard_capture.py`)
- Añadir selector resolución/escala (`layout_settings.py` / `appearance.py`)
- Validar que la imagen reconstruida arranca con los nuevos paquetes
