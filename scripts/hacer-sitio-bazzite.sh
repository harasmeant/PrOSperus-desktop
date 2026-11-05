#!/usr/bin/env bash
# Encoge el btrfs de Bazzite (nvme0n1p3) y su partición para dejar espacio
# libre al final del NVMe, donde luego instala prosperus-instalar-disco.
# Uso (desde Bazzite):  sudo bash scripts/hacer-sitio-bazzite.sh [GiB] [--simular]
# Por defecto deja 150 GiB libres. No crea ni formatea nada.
set -euo pipefail

GIB=150; SIMULAR=0
for a in "$@"; do
  case "$a" in
    --simular) SIMULAR=1 ;;
    ''|*[!0-9]*) echo "Argumento no válido: $a" >&2; exit 1 ;;
    *) GIB=$a ;;
  esac
done

DISCO=/dev/nvme0n1; PART=${DISCO}p3; N=3; MP=/var/home
MIB=$((1024 * 1024)); GIB_B=$((1024 * MIB))

[[ $EUID -eq 0 ]] || { echo "Hace falta sudo." >&2; exit 1; }
[[ $(blkid -s LABEL -o value "$PART") == bazzite && $(blkid -s TYPE -o value "$PART") == btrfs ]] \
  || { echo "$PART no es el btrfs «bazzite». No toco nada." >&2; exit 1; }
[[ $(findmnt -no SOURCE "$MP" | sed 's/\[.*//') == "$PART" ]] \
  || { echo "$MP no está en $PART. No toco nada." >&2; exit 1; }
[[ $(lsblk -nro NAME "$DISCO" | tail -1) == nvme0n1p3 ]] \
  || { echo "p3 no es la última partición. No toco nada." >&2; exit 1; }

SECTOR=$(blockdev --getss "$DISCO")
FS=$(btrfs filesystem show --raw "$MP" | awk '/devid/{print $4; exit}')
USADO=$(btrfs filesystem usage -b "$MP" | awk '/Device allocated:/{print $3}')
NUEVO_FS=$((FS - (GIB + 1) * GIB_B))
(( NUEVO_FS > USADO + 30 * GIB_B )) \
  || { echo "No cabe: quedarían menos de 30 GiB de margen para Bazzite." >&2; exit 1; }

echo "btrfs ahora: $((FS / GIB_B)) GiB (reservado $((USADO / GIB_B)) GiB)"
echo "btrfs nuevo: $((NUEVO_FS / GIB_B)) GiB · libres al final: ~${GIB} GiB"
if (( SIMULAR )); then echo "(simulación: no he cambiado nada)"; exit 0; fi
read -rp "Escribe ENCOGER para seguir: " r; [[ $r == ENCOGER ]] || exit 1

COPIA=/var/home/${SUDO_USER:-root}/tabla-particiones-antes-$(date +%F-%H%M).sfdisk
sfdisk -d "$DISCO" > "$COPIA"; echo "Copia de la tabla: $COPIA"

echo "Encogiendo btrfs (puede tardar si tiene que mover datos)…"
btrfs filesystem resize "1:$NUEVO_FS" "$MP"
FS=$(btrfs filesystem show --raw "$MP" | awk '/devid/{print $4; exit}')
(( FS <= NUEVO_FS )) || { echo "El btrfs no ha encogido. Paro antes de tocar la partición." >&2; exit 1; }

# Partición = btrfs + 1 GiB de margen, redondeada a MiB.
BYTES=$(( (FS + GIB_B + MIB - 1) / MIB * MIB ))
SECTORES=$((BYTES / SECTOR))
echo ",$SECTORES" | sfdisk --no-reread --no-tell-kernel -N $N "$DISCO"
resizepart "$DISCO" $N "$SECTORES"

echo; lsblk -o NAME,SIZE,FSTYPE,LABEL "$DISCO"; echo; sfdisk -F "$DISCO"
echo "Listo. Ahora arranca el USB de PrOSperus y sigue el paso 2 de docs/DUAL-BOOT.md."
