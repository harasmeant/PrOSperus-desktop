# Pruebas mínimas

Lista para dar por buena una ISO. Se repite en cada sistema base y se marca
lo comprobado con fecha. Ninguna ISO está probada todavía en hardware real.

- ISO Fedora: `scripts/build-iso.sh` → `out/iso/`
- ISO Arch: `scripts/build-iso-arch.sh` → `out/iso-arch/` (ver [ARCH.md](ARCH.md))
- ISO Debian: `scripts/build-iso-debian.sh` → `out/iso-debian/` (ver [DEBIAN.md](DEBIAN.md))

Marca: `[x]` funciona · `[!]` falla (anota qué) · `[ ]` sin probar.

## 1. Arranque

| Prueba | Fedora VM | Fedora real | Arch VM | Arch real | Debian VM | Debian real |
|---|---|---|---|---|---|---|
| Arranca por UEFI hasta el escritorio sin pedir nada | [x] | [ ] | [x] 04-11 | [ ] | [x] 04-11 | [ ] |
| Arranca con Secure Boot activo (o avisa claramente) | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Pantalla correcta en la gráfica integrada | — | [ ] | — | [ ] | — | [ ] |
| Pantalla correcta con NVIDIA (portátil híbrido) | — | [ ] | — | [ ] | — | [ ] |
| Monitor externo por HDMI | — | [ ] | — | [ ] | — | [ ] |
| Apagar y reiniciar desde el escritorio | [x] | [ ] | [ ] | [ ] | [ ] | [ ] |

## 2. Hardware básico

| Prueba | Fedora real | Arch real | Debian real |
|---|---|---|---|
| Teclado en español (ñ, tildes) | [ ] | [ ] | [ ] |
| Ratón y panel táctil, cursor visible | [ ] | [ ] | [ ] |
| Wi-Fi: ver redes, conectar, sobrevive a reiniciar (USB persistente) | [ ] | [ ] | [ ] |
| Red por cable | [ ] | [ ] | [ ] |
| Sonido: altavoces, auriculares, teclas de volumen con barra | [ ] | [ ] | [ ] |
| Brillo de pantalla con las teclas | [ ] | [ ] | [ ] |
| Bluetooth: emparejar un dispositivo | [ ] | [ ] | [ ] |
| Suspender y volver | [ ] | [ ] | [ ] |

## 3. Escritorio

| Prueba | Fedora | Arch | Debian |
|---|---|---|---|
| Mapa, tarjetero y fondos se ven bien | [x] | [x] 04-11 (VM) | [x] 04-11 (VM) |
| Crear proyecto, crear nota, escribir, guardar | [x] | [ ] | [ ] |
| Buscar una nota por una palabra de su contenido | [x] | [ ] | [ ] |
| Copiar/pegar notas y carpetas | [ ] | [ ] | [ ] |
| Aplicaciones (Ctrl+Espacio): lista y abre programas | [ ] | [x] 04-11 (VM) | [x] 04-11 (VM) |
| Consola (Foot) abre en la carpeta del proyecto | [ ] | [ ] | [x] 04-11 (VM) |
| Ventanas: Fibonacci, mover, minimizar, cerrar | [ ] | [ ] | [ ] |
| Captura de pantalla y portapapeles | [ ] | [ ] | [ ] |
| Bloqueo de pantalla (Super+L) y desbloqueo | [ ] | [ ] | [ ] |
| Fondo animado (Sistema › Fondo) con GPU | [ ] | [ ] | [ ] |
| Asistente Claude: inicia sesión y responde | [ ] | [ ] | [ ] |

## 4. Instalar programas (requiere red)

| Prueba | Fedora | Arch | Debian |
|---|---|---|---|
| Buscar un programa del sistema y de Flathub | [ ] | [x] 04-11 (VM, sin red) | [x] 04-11 (VM, sin red) |
| Instalar un paquete del sistema (p. ej. `htop`) | [ ] | [ ] | [ ] |
| Instalar uno de Flathub (p. ej. Firefox) y que salga en Aplicaciones | [ ] | [ ] | [ ] |
| Instalar un paquete local (`.rpm` / `.pkg.tar.zst` / `.deb`) | [ ] | [ ] | [ ] |
| Asistente de controladores: detecta la gráfica | [ ] | [ ] | [ ] |
| NVIDIA propietario: instala, reinicia y carga | [ ] | [ ] | [ ] |

## 5. USB persistente (`scripts/write-usb.sh`)

| Prueba | Fedora | Arch | Debian |
|---|---|---|---|
| Notas y ajustes siguen tras reiniciar | [ ] | [ ] | [ ] |
| Wi-Fi guardada sigue tras reiniciar | [ ] | [ ] | [ ] |
| Programas de Flathub siguen tras reiniciar | [ ] | [ ] | [ ] |
| Programas del sistema siguen tras reiniciar (capa del sistema) | [ ] | [ ] | [ ] |
| Grabar una ISO nueva no borra la carpeta personal | [ ] | [ ] | [ ] |

## Registro

Anota aquí cada sesión de pruebas: fecha, equipo, ISO (SHA-256 corto) y fallos.

- 2026-11-04 · QEMU/KVM, 2 GiB, sin red · Arch: arranque, escritorio,
  Aplicaciones y búsqueda en Instalar programas correctos.
- 2026-11-04 · QEMU/KVM, 2 GiB, sin red · Debian (ISO 038c00d5): arranque,
  escritorio, Aplicaciones, consola sin errores de configuración, búsqueda con
  apt y Flathub correctas; sin bucle de wob. Corregido antes: SwayFX 0.5.1
  dejaba un recuadro oscuro sin repintar al abrir Buscar (ahora 0.5.3).
