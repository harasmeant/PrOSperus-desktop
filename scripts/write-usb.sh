#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Graba la ISO Live en un USB y añade la partición PROSPERUS_DATA (ext4) con el
# espacio libre: ahí se guardan /home/prosperus y las redes Wi-Fi entre arranques.
# Uso: write-usb.sh ISO DESTINO   (DESTINO = /dev/sdX o un archivo de imagen para QEMU)
set -euo pipefail
iso=${1:?Uso: write-usb.sh ISO DESTINO}
target=${2:?Uso: write-usb.sh ISO DESTINO}
test -f "$iso" || { echo "No existe la ISO: $iso" >&2; exit 1; }

if [[ -b $target ]]; then
    (( EUID == 0 )) || { echo 'Ejecuta con sudo.' >&2; exit 1; }
    read -r rm tran < <(lsblk -dno RM,TRAN "$target")
    if [[ $rm != 1 && $tran != usb ]]; then
        echo "$target no parece un USB extraíble; no se toca." >&2; exit 1
    fi
    if [[ -n $(lsblk -nro MOUNTPOINTS "$target" | tr -d '[:space:]') ]]; then
        echo "$target tiene particiones montadas; desmóntalas antes." >&2; exit 1
    fi
    lsblk -o NAME,SIZE,MODEL,TRAN "$target"
    read -rp "Se borrará TODO el contenido de $target. Escribe SI para continuar: " answer
    [[ $answer == SI ]] || { echo 'Cancelado.'; exit 1; }
    wipefs -aq "$target"
    dd if="$iso" of="$target" bs=4M conv=fsync status=progress
else
    # Imagen de prueba: arranca en QEMU como si fuera un USB.
    cp "$iso" "$target"
    truncate -s "${PROSPERUS_USB_SIZE:-8G}" "$target"
fi

# La copia de seguridad del GPT queda al final de la ISO: se lleva al final del
# medio para que el espacio libre pueda usarse.
sfdisk --relocate gpt-bak-std "$target"
printf 'name=PROSPERUS_DATA, type=linux\n' | sfdisk --append --no-reread --no-tell-kernel "$target"
read -r start size sector < <(sfdisk --json "$target" | python3 -c '
import json, sys
t = json.load(sys.stdin)["partitiontable"]
p = t["partitions"][-1]
print(p["start"], p["size"], t.get("sectorsize", 512))')

if [[ -b $target ]]; then
    partprobe "$target"
    udevadm settle
    part=$(lsblk -lnpo NAME "$target" | tail -1)
    mkfs.ext4 -F -q -L PROSPERUS_DATA -m 0 "$part"
    sync
else
    mkfs.ext4 -F -q -L PROSPERUS_DATA -m 0 -E offset=$(( start * sector )) \
        "$target" $(( size * sector / 1024 ))
fi
echo "Listo: $target arranca PrOSperus. Lo que guardes en /home/prosperus queda en la partición PROSPERUS_DATA."
