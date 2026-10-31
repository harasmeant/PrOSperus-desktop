# Persistencia / Instalación básica
# SPDX-License-Identifier: GPL-3.0-only

Estado: en progreso (autorizado sin parar).

## Problema actual
ISO Live usa overlay en RAM (`rd.live.overlay.overlayfs=1`). Al apagar, los cambios se pierden.

## Solución para VM / imagen instalada
- Eliminar `rd.live.ram` del cmdline si se quiere persistencia en disco.
- Usar `root=/dev/sda2` (o LABEL) con `rw` y fstab generado.
- El instalador (`scripts/install.sh` pendiente) debe:
  1. Particionar disco (EFI + root ext4)
  2. Copiar rootfs (tar o rsync)
  3. Instalar bootloader (systemd-boot / GRUB) en EFI
  4. Generar `/etc/fstab`, `/etc/machine-id`, usuario `prosperus`

## Para la imagen qcow2 actual (VM de prueba)
- Copiar `prosperus.qcow2` como disco persistente (no overlay) si se desea conservar cambios entre reinicios.
- En `run-vm.sh` utilizar `-snapshot=off` y permitir escritura directa al disco.
