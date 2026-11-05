# Dual boot con Windows · guía para IT
<!-- SPDX-License-Identifier: GPL-3.0-only -->

Instalar PrOSperus (ISO Debian 13) junto a Windows en un portátil gestionado.
Detalles del instalador en [DUAL-BOOT.md](DUAL-BOOT.md). Probado en QEMU y en
un portátil con Bazzite; **no probado todavía junto a Windows**.

> **Aviso de seguridad:** el núcleo de PrOSperus está fijado y no recibe parches;
> no hay Secure Boot. Ver el aviso del [README](../README.md).

## Qué hace el instalador

`prosperus-instalar-disco` (incluido en la ISO):

- Crea **una** partición ext4 (`PROSPERUS_ROOT`, tipo Linux root x86-64) en el
  hueco sin asignar más grande. No borra, mueve ni redimensiona nada, y compara
  la tabla GPT antes y después.
- Copia un UKI en `ESP:\EFI\prosperus\prosperus.efi`. No toca `EFI\Microsoft` ni
  `EFI\Boot`. No instala GRUB ni otro gestor de arranque.
- Añade la entrada NVRAM `PrOSperus` **al final** de `BootOrder`. Windows sigue
  arrancando por defecto; PrOSperus se elige en el menú de arranque del firmware.

## Requisitos

| | |
|---|---|
| Firmware | UEFI, disco GPT, una sola ESP en el disco |
| Secure Boot | **Desactivado** (ni la ISO ni el UKI están firmados) |
| Espacio | ≥ 30 GiB sin asignar (recomendado 100 GiB o más) |
| ESP | **≥ 53 MiB libres**. La ESP por defecto de Windows (100 MiB) suele no tenerlos |
| Medio | USB de ≥ 8 GB grabado con `scripts/write-usb.sh` (lo borra entero) |

## Pasos

### En Windows

1. **Clave de recuperación de BitLocker** a mano (Entra ID / AD / `manage-bde -protectors -get C:`).
2. Suspender BitLocker para el próximo reinicio o dos, porque cambiar la NVRAM o Secure Boot dispara la petición de clave:
   ```
   manage-bde -protectors -disable C: -RebootCount 3
   ```
3. Desactivar el **inicio rápido** (Opciones de energía) o la hibernación (`powercfg /h off`),
   para que Windows no deje el disco en un estado a medias.
4. Comprobar el espacio libre de la ESP:
   ```
   mountvol S: /s
   fsutil volume diskfree S:
   mountvol S: /d
   ```
   Si tiene menos de 53 MiB libres, ver «ESP pequeña» más abajo.
5. **Encoger C:** desde Administración de discos (`diskmgmt.msc`) → *Reducir volumen*.
   Dejar el hueco **sin asignar**: no crear partición ni formatear.

### En el firmware

6. Desactivar Secure Boot. Arrancar el USB desde el menú de arranque (F9 en los HP).

### En PrOSperus Live

7. Abrir la consola. Simular primero, sin escribir nada:
   ```bash
   lsblk -po NAME,SIZE,TYPE,FSTYPE,PARTTYPENAME,LABEL
   sudo prosperus-instalar-disco --disco /dev/nvme0n1 --simular
   ```
8. Si el plan es correcto, instalar (opcional `--tamano <GiB>`). Pide escribir
   `INSTALAR` y la contraseña del usuario `prosperus`:
   ```bash
   sudo prosperus-instalar-disco --disco /dev/nvme0n1
   ```
9. Reiniciar sin el USB. Arranca Windows: comprobar que entra y que BitLocker no
   pide clave. Después, menú del firmware → **PrOSperus**.

## ESP pequeña

El instalador se detiene sin escribir nada si no cabe. Opciones, de menos a más invasiva:

- Liberar espacio en la ESP (fuentes o idiomas de `EFI\Microsoft\Boot\Fonts`, restos
  de otros sistemas). **No** borrar `bootmgfw.efi`, `BCD` ni `EFI\Boot`.
- Ampliar la ESP: requiere mover o encoger la partición contigua (normalmente MSR
  y C:). Hacerlo con herramientas propias de IT; el instalador no lo hace a propósito.

## Problemas conocidos

- **Windows Update o el firmware pueden reordenar o borrar la entrada** de PrOSperus
  de la NVRAM. Para recrearla desde la Live, con `N` = número de la ESP:
  `sudo efibootmgr --create --disk /dev/nvme0n1 --part N --label PrOSperus --loader '\EFI\prosperus\prosperus.efi'`
  y después reordenar con `efibootmgr -o` para dejar Windows primero.
- **Reactivar Secure Boot** impide arrancar PrOSperus (Windows sigue funcionando).
- **Hora:** Linux usa UTC en el reloj de hardware y Windows hora local; si la hora
  sale desfasada en uno de los dos, en PrOSperus: `sudo timedatectl set-local-rtc 1`.

## Desinstalar

1. En Windows (`diskmgmt.msc`): borrar la partición `PROSPERUS_ROOT` y ampliar C:.
2. Borrar la carpeta de la ESP: `mountvol S: /s`, luego `rmdir /s S:\EFI\prosperus`, luego `mountvol S: /d`.
3. Borrar la entrada NVRAM: `bcdedit /enum firmware` → `bcdedit /delete {id}`.
4. Reactivar Secure Boot y BitLocker (`manage-bde -protectors -enable C:`).
