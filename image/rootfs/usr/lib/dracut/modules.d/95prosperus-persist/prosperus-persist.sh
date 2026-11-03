#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Initramfs: si el USB del que se arranca tiene PROSPERUS_DATA, los cambios del
# sistema (programas de Fedora, controladores, /etc) se guardan en ella en vez de
# en la RAM. Cualquier fallo deja la sesión en RAM: nunca bloquea el arranque.
data=/run/prosperus-data
say() { echo "prosperus-persist: $*"; }

dev=
i=0
while [ $i -lt 10 ]; do
    dev=$(blkid -L PROSPERUS_DATA 2>/dev/null) && break
    sleep 0.5; i=$((i + 1))
done
[ -n "$dev" ] || { say 'sin PROSPERUS_DATA: sistema en RAM.'; exit 0; }

part=/sys/class/block/${dev##*/}
[ -e "$part/partition" ] || { say "$dev no es una partición: no se usa."; exit 0; }
parent=$(basename "$(readlink -f "$part/..")")
# Solo la partición del propio USB de PrOSperus: nunca un disco interno del equipo.
if [ "$(blkid -s LABEL -o value "/dev/$parent" 2>/dev/null)" != PROSPERUS_LIVE ]; then
    say "/dev/$parent no es el USB de PrOSperus: no se toca."; exit 0
fi

# El disco entero está montado como iso9660 y el kernel no deja abrir la partición:
# se accede por un loop con desplazamiento.
loop=$(losetup -f --show --offset $(( $(cat "$part/start") * 512 )) \
    --sizelimit $(( $(cat "$part/size") * 512 )) "/dev/$parent") || { say 'loop fallido.'; exit 0; }
fsck.ext4 -p "$loop"
if [ $? -ge 4 ]; then
    say 'PROSPERUS_DATA tiene errores que fsck no corrige solo: sistema en RAM.'
    losetup -d "$loop"; exit 0
fi
mkdir -p "$data"
mount -o noatime "$loop" "$data" || { say 'no se pudo montar.'; losetup -d "$loop"; exit 0; }

build=$(cat /run/rootfsbase/usr/share/prosperus/build-id 2>/dev/null) || build=sin-version
sys=$data/sistema
mkdir -p "$sys"
# Volver al sistema recién instalado: crear el archivo REINICIAR en «sistema».
if [ -e "$sys/REINICIAR" ]; then
    say 'REINICIAR: se descarta la capa del sistema.'
    rm -rf "$sys/$build" "$sys/REINICIAR"
fi
# Las capas de otras versiones de la ISO no encajan con esta imagen base.
for old in "$sys"/*; do
    [ -d "$old" ] && [ "$old" != "$sys/$build" ] && { say "se descarta la capa de ${old##*/}."; rm -rf "$old"; }
done
# Con menos de 1 GiB libre la capa llenaría el USB a mitad de una instalación.
free=$(df -Pk "$data" | awk 'NR==2 {print $4}' 2>/dev/null)
if [ -n "$free" ] && [ "$free" -lt 1048576 ]; then
    say 'menos de 1 GiB libre: sistema en RAM (la carpeta personal sí se conserva).'; exit 0
fi
mkdir -p "$sys/$build/upper" "$sys/$build/work"
rmdir /run/overlayfs /run/ovlwork 2>/dev/null
if [ -e /run/overlayfs ] || [ -e /run/ovlwork ]; then
    say 'la capa en RAM ya existe: sistema en RAM.'; exit 0
fi
ln -s "$sys/$build/upper" /run/overlayfs
ln -s "$sys/$build/work" /run/ovlwork
: > /run/prosperus-system-persistent
say "sistema persistente en PROSPERUS_DATA (versión $build)."
