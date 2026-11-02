<!-- SPDX-License-Identifier: GPL-3.0-only -->
# Terminal, red y Python en PrOSperus

## Terminal
- **Programa**: foot
- **Accesos directos**: Super+Intro, o Aplicaciones → foot
- **Modo**: ventana flotante (Fibonacci) o pantalla completa (Super+F)
- **Atajos**: Super+Q (cerrar), Super+D (ocultar/mostrar apps), Super+Esc (volver al mapa), Alt+Tab (cambiar app)
- **Directorio inicial**: desde Aplicaciones, la carpeta del proyecto abierto en el mapa; con Super+Intro, la carpeta personal

## Red
- NetworkManager activo
- **VM (scripts/run-vm.sh)**: red cable configurada automáticamente; comprobar con `ping -c 3 fedoraproject.org` y `nmcli device status`
- **Wi-Fi en hardware**: listar con `nmcli device wifi list`, conectar con `nmcli device wifi connect NOMBRE --ask`
- **Comprobación rápida**: `ping -c 3 fedoraproject.org`

## Instalar programas
- `dnf search palabra` busca; `sudo dnf install paquete` instala.
- En la imagen de desarrollo `sudo` no pide contraseña; una instalación real deberá pedirla.
- VSCodium, Blender, FreeCAD, Steam, Lutris y Zen están preparados en `image/Containerfile.apps`, pero todavía no se incluyen.

## Python
- Python 3 integrado; pip incluido
- **Flujo recomendado por proyecto**:
  1. `python3 -m venv .venv`
  2. `source .venv/bin/activate`
  3. `pip install paquete`
- **Editar**: `nano archivo.py`
- **Ejecutar**: `python3 archivo.py`
- **Git** incluido; no usar `sudo pip install` (rompe paquetes). Usar `sudo dnf install python3-paquete` o venv.
- **Persistencia**: la VM arranca con `snapshot=on`; paquetes y archivos se pierden al apagar. Ver `docs/PERSISTENCIA.md` (pendiente).
