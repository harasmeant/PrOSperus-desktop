# Dual boot: PrOSperus (Arch o Debian) junto a Bazzite

**Estado al 04-11-2026:** instalador probado en QEMU con un disco virtual que
imita el del portátil (`scripts/test-install-arch.sh`, Arch; el 05-11-2026 también
Debian con `scripts/test-install-arch.sh debian`). No probado todavía en
hardware real. Sin Secure Boot (ver «Límites»).

Las ISO de Arch y de Debian traen `prosperus-instalar-disco`, que instala PrOSperus en el
**espacio libre** de un disco, al lado del sistema que ya hay.

Junto a Windows (BitLocker, ESP pequeña, Secure Boot): [DUAL-BOOT-WINDOWS.md](DUAL-BOOT-WINDOWS.md).

## Qué hace y qué no

- Crea **una partición nueva** en espacio sin asignar (ext4, `PROSPERUS_ROOT`).
  No borra, mueve, formatea ni redimensiona ninguna partición existente, y
  comprueba al final que la tabla de las demás sigue idéntica.
- En la partición EFI existente solo añade `EFI/prosperus/prosperus.efi`
  (unos 50 MiB). No toca `EFI/fedora` ni nada más.
- Añade la entrada **PrOSperus** al **final** del orden de arranque: Bazzite
  sigue arrancando por defecto. PrOSperus se elige con **F9** al encender (HP).
- Pide una contraseña para el usuario `prosperus` (sudo y bloqueo de pantalla).
  La sesión entra sola, como en el USB.
- Guarda una copia de la tabla de particiones anterior en
  `/usr/share/prosperus/tabla-particiones-antes.sfdisk` del sistema instalado.
- No toca el disco del NAS (`FotosNAS`), salvo que se le indique ese disco con `--disco`.
  Aun así no podría hacer nada en él: no tiene partición EFI ni espacio libre.

## Paso 1 · Hacer sitio (una vez, con cuidado)

Ahora el NVMe lo ocupa entero Bazzite (btrfs). Hay que encoger su partición
para dejar espacio libre al final. **Antes, copia de seguridad de lo importante.**

Desde Bazzite (btrfs se puede encoger estando montado), en una terminal:

```bash
sudo bash scripts/hacer-sitio-bazzite.sh 150 --simular   # solo enseña el plan
sudo bash scripts/hacer-sitio-bazzite.sh 150             # pide escribir ENCOGER
```

Encoge el btrfs `bazzite` (GiB pedidos + 1), luego la partición 3 dejando
1 GiB de margen sobre el sistema de archivos, y guarda antes la tabla en
`~/tabla-particiones-antes-*.sfdisk`. Se niega si Bazzite se quedaría con
menos de 30 GiB de margen o si `nvme0n1p3` no es la última partición.

Este paso es el único con riesgo para Bazzite: hazlo con calma, y si hay
dudas, pide ayuda antes de pulsar. El instalador no lo hace por ti a propósito.

## Paso 2 · Instalar

1. Arranca el USB de PrOSperus (Arch) con F9.
2. Abre la consola y simula primero, para ver qué hará sin escribir nada:
   ```bash
   sudo prosperus-instalar-disco --disco /dev/nvme0n1 --simular
   ```
3. Si el plan es correcto, instala (opcional `--tamano 120` para usar solo 120 GiB):
   ```bash
   sudo prosperus-instalar-disco --disco /dev/nvme0n1
   ```
   Pide escribir `INSTALAR` y la contraseña dos veces. Tarda unos minutos.
4. Reinicia sin el USB, pulsa F9 y elige **PrOSperus**.

## Probar sin hardware

```bash
bash scripts/build-iso-arch.sh
bash scripts/test-install-arch.sh          # o, con la ISO de Debian: ... debian
```

Crea `out/iso-arch/prueba-disco/disco.raw` (EFI con un «Bazzite» falso,
`/boot`, sistema y 40 GiB libres), instala sin intervención, arranca el disco
y comprueba byte a byte que las particiones de «Bazzite» no han cambiado.
Captura del escritorio en `out/iso-arch/prueba-disco/escritorio.png`.

## Límites

- **Sin Secure Boot.** Ni la ISO ni el `prosperus.efi` instalado están firmados.
  Con el firmware en Setup Mode (como ahora), Bazzite y PrOSperus arrancan
  igual. Para el anticheat de Bazzite haría falta activarlo: el plan es crear
  claves propias con `sbctl` conservando las de Microsoft y firmar `prosperus.efi`.
- El núcleo está fijado (`IgnorePkg = linux linux-headers`) como en la Live:
  `pacman -Syu` no lo actualiza, porque el `prosperus.efi` de la partición EFI
  no se regenera solo todavía.
- GRUB de Bazzite no muestra PrOSperus; se elige con el menú del firmware (F9).
- Para desinstalar: borrar la partición `PROSPERUS_ROOT`, la carpeta
  `EFI/prosperus` y la entrada (`sudo efibootmgr -b NNNN -B`).
