# Persistencia en el USB
<!-- SPDX-License-Identifier: GPL-3.0-only -->

`scripts/write-usb.sh` graba la ISO y dedica **todo el espacio restante** del USB a la
partición ext4 `PROSPERUS_DATA`. Con ella, el USB funciona como un sistema instalado:
lo que se instala o configura se conserva al apagar.

## Qué se guarda y dónde

| En `PROSPERUS_DATA` | Contenido | Si se graba una ISO nueva |
| --- | --- | --- |
| `sistema/<versión>/` | Capa de cambios del sistema (overlayfs): programas de Fedora (dnf), controladores (akmod-nvidia), `/etc` | Se descarta: no encaja con otra imagen base |
| `home/` | `/home/prosperus`: proyectos, configuración, Claude Code | Se conserva |
| `flatpak/` | Programas de Flathub | Se conserva |
| `system-connections/` | Redes Wi-Fi | Se conserva |
| `journal/` | Registro del sistema (diagnóstico) | Se conserva |

Grabar con `write-usb.sh` formatea el USB entero: para conservar algo al cambiar de ISO,
haz antes una copia de `home/`.

## Cómo funciona

- El initramfs monta el disco USB entero como iso9660, y el kernel no deja abrir la
  partición 4 mientras tanto. Se accede a ella con un loop con desplazamiento.
- Módulo dracut `prosperus-persist` (en `image/rootfs/usr/lib/dracut/modules.d/`):
  se ejecuta tras encontrar el medio Live y antes de montar la raíz. Monta
  `PROSPERUS_DATA` en `/run/prosperus-data` y apunta `/run/overlayfs` y `/run/ovlwork`
  (la capa de escritura de dmsquash-live) a `sistema/<versión>`. La versión está en
  `/usr/share/prosperus/build-id`.
- `prosperus-persistence.service`, en el sistema arrancado, monta con bind la carpeta
  personal, Flathub, las redes y el registro.
- dnf no instala núcleos (`excludepkgs` en `/etc/dnf/dnf.conf`): el arranque usa siempre
  el núcleo de la ISO.

## Salvaguardas

- Solo se usa una `PROSPERUS_DATA` que sea partición del disco con etiqueta
  `PROSPERUS_LIVE` (el propio USB). Los discos internos no se montan ni se escriben.
- Si fsck no puede reparar la partición o quedan menos de 1 GiB libres, el sistema
  arranca en RAM; la carpeta personal se sigue conservando si se puede montar.
- **Volver al sistema recién grabado** sin perder la carpeta personal: crear el archivo
  `sistema/REINICIAR` en `PROSPERUS_DATA` (desde PrOSperus:
  `sudo touch /run/prosperus-data/sistema/REINICIAR`, o desde otro equipo con el USB
  montado). Al arrancar, la capa del sistema se descarta.
