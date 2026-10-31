# Estado VM / Lista de mínimos para funcionamiento

**Fecha de actualización:** 2026-10-31

## Estado actual (confirmado en QEMU con UEFI)
- Arranque UEFI de la ISO/imagen `prosperus-boxes.qcow2` comprobado.
- Sesión gráfica (`greetd` + Cage + PrOSperus) inicia.
- **QA pendiente:** ratón invisible, pantalla dividida (4 cuartos / layout Fibonacci/ultrawide), falta selector de resolución y escala.
- No se valida en Boxes por completo; requiere ajuste de firmware UEFI.
- No hay red, persistencia ni instalador.

## Problemas encontrados (QA)
- [ ] Ratón no visible / no capturado en VM.
- [ ] Pantalla dividida por defecto (perfil layout activo).
- [ ] Falta selector de resolución (`xrandr` / Qt settings).
- [ ] Falta selector de escala (DPI / escala de interfaz).
- [ ] No hay persistencia tras reiniciar.
- [ ] No hay red en la VM (no probado con `-nic` en `run-iso.sh`).

## Requisitos mínimos para funcionar adecuadamente
- Firmware UEFI (OVMF) — no SeaBIOS.
- 2 vCPU, 2 GiB RAM ( mínimo 1024 MiB para prueba reducida).
- `systemd-pam` incluido (ya corregido en `Containerfile.base`).
- Driver gráfico `virtio-vga` o `qxl` con Mesa.
- Teclado/mouse `virtio` (ya configurado en `run-vm.sh`).
- Resolución dinámica o fija (1360×850 o 900×650 según pruebas locales).
- Selector de disposición (layout) y escala de ventana.

## Aplicaciones / integración que deben funcionar según proyecto
Según `README.md` y la demo (`demo-system/`, `prototype/`):
- [ ] PrOSperus desktop independiente (`desktop/prosperus/`): mapa, notas flotantes, tarjetero, barra contextual.
- [ ] Buscador de aplicaciones Linux (`GIO` + `glib`): lanzar apps detectadas.
- [ ] Edición Markdown (`Qt`/`pyside6`).
- [ ] Gestión de archivos (crear, copiar, pegar, duplicar, importar proyectos).
- [ ] Notas flotantes (`Hover Editor` / mecanismo de miniminización).
- [ ] Favoritos de aplicaciones globales (archivo de config).
- [ ] Teclado: `F1`, `Ctrl+Espacio`, `Ctrl+Alt+N`, `Super+E/D/I`, navegación `Alt+Flechas`.
- [ ] Controles de sesión: volumen (`playerctl`), brillo (`brightnessctl`), `wpctl` (audio).
- [ ] Integración con `VSCodium` (apertura de archivos `.py` vía protocolo de escritorio).

## Acciones para completar
1. Añadir selector de resolución/escala al escritorio (`appearance.py` / `layout_settings.py`).
2. Corregir captura de ratón en QEMU/Boxes (probablemente `virtio-mouse` o evento Qt).
3. Probar disposición por defecto (sin layout Fibonacci si causa división no deseada).
4. Instalar/asegurar paquetes de aplicaciones en el contenedor base (`Containerfile.base` / `Containerfile`): `gimp`, `gedit`, `firefox`, `libreoffice`, `vscodium` (opcional pero documentado).
5. Añadir `networkmanager` y `wireless-tools` para red real.
6. Validar comportamiento en Boxes con UEFI confirmada.
