# Selector básico de resolución y escala
# SPDX-License-Identifier: GPL-3.0-only

# Devuelve pares (resolución, etiqueta) para el menú de selección.
def available_resolutions():
    return [
        ("1360x850", "Estándar (referencia demo)"),
        ("900x650", "Compacto"),
        ("1920x1080", "Full HD"),
        ("auto", "Automático / pantalla"),
    ]

# Aplica la resolución con xrandr en la salida DP-1; ignora errores si el modo no existe.
def apply_resolution(width, height):
    import os
    try:
        os.system(f"xrandr --output DP-1 --mode {width}x{height} 2>/dev/null || true")
    except Exception:
        pass

# Factor de escala predeterminado (1.0 = sin escalado).
def scale_factor():
    return 1.0
