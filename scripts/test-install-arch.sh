#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Prueba del instalador a disco (dual boot) en una VM, con un disco virtual que
# imita el del portátil: partición EFI con un «Bazzite» falso, /boot, sistema y
# espacio libre. Nunca usa discos reales: todo son archivos en out/iso-<distro>/prueba-disco.
# Uso: bash scripts/test-install-arch.sh [arch|debian]   (por defecto arch)
#   1. Arranca la ISO, ejecuta prosperus-instalar-disco sin intervención y apaga.
#   2. Arranca desde el disco virtual (sin ISO) por la entrada «PrOSperus».
#   3. Comprueba que las particiones existentes siguen intactas.
set -euo pipefail
cd "$(dirname "$0")/.."
distro=${1:-arch}
iso=out/iso-$distro/prosperus-live-x86_64.iso
dir=out/iso-$distro/prueba-disco
# La VM de prueba usa siempre las herramientas de Arch (tienen sfdisk y mtools).
tools=localhost/prosperus-arch-tools:dev
test -f "$iso" && test -w /dev/kvm
rm -rf "$dir" && mkdir -p "$dir"
# Núcleo e initramfs de la misma imagen que la ISO: la fase 1 los arranca
# directamente para poder añadir la orden de instalación a la línea del núcleo.
podman run --rm --network=none --security-opt label=disable -v "$PWD/$dir:/o" \
    localhost/prosperus-$distro-live:dev cp /boot/vmlinuz-prosperus /boot/initramfs-prosperus.img /o/
podman run -i --rm --network=none --device /dev/kvm --cpus=2 --memory=2560m --memory-swap=2560m \
    --security-opt label=disable -v "$PWD/$dir:/o" -v "$PWD/$iso:/iso/live.iso:ro" \
    "$tools" bash -s <<'EOF'
set -euo pipefail
cd /o
mib=$((1024 * 1024))
fail() { echo "PRUEBA FALLIDA: $*"; exit 1; }

# Disco de 50 GiB (disperso): EFI 600 MiB, xboot 1 GiB, «bazzite» 8 GiB, 40 GiB libres.
truncate -s 50G disco.raw
printf 'label: gpt\nsize=600MiB, type=U, name="EFI System Partition"\nsize=1GiB, type=L, name=xboot\nsize=8GiB, type=L, name=bazzite\n' \
    | sfdisk -q disco.raw
mkfs.vfat -F 32 --offset=2048 disco.raw $((600 * 1024)) >/dev/null
head -c 300000 /dev/urandom > shimx64.efi
mmd -i disco.raw@@1M ::/EFI ::/EFI/fedora
mcopy -i disco.raw@@1M shimx64.efi ::/EFI/fedora/shimx64.efi
mkdir -p datos && head -c 5000000 /dev/urandom > datos/fotos.bin
mke2fs -q -t ext4 -L bazzite_xboot -d datos -E offset=$((1230848 * 512)) disco.raw 1G
mke2fs -q -t ext4 -L bazzite -d datos -E offset=$((3328000 * 512)) disco.raw 8G
sfdisk --dump disco.raw | grep '^disco' > tabla-antes.txt
part_sum() { dd if=disco.raw bs=1M skip=$(( $1 * 512 / mib )) count=$(( $2 * 512 / mib )) status=none | sha256sum | cut -d' ' -f1; }
sums() { awk -F'[=, ]+' 'NR > 1 {print $4, $6}' tabla-antes.txt | while read -r s n; do part_sum "$s" "$n"; done; }
sums > sumas-antes.txt
cp /usr/share/edk2/ovmf/OVMF_VARS.fd vars.fd

qemu() {
    timeout "$1" qemu-system-x86_64 -machine q35,accel=kvm -cpu host -smp 2 -m 2048 \
        -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
        -drive if=pflash,format=raw,file=vars.fd -device virtio-vga \
        -display none -nic none -no-reboot "${@:2}"
}

echo '== Fase 1: instalar desde la Live'
qemu 40m -kernel vmlinuz-prosperus -initrd initramfs-prosperus.img \
    -drive file=disco.raw,format=raw,if=virtio -cdrom /iso/live.iso -serial file:serie-1.log \
    -append 'root=live:CDLABEL=PROSPERUS_LIVE rd.live.image rd.live.overlay.overlayfs=1 rw console=tty0 console=ttyS0,115200 selinux=0 systemd.setenv=PROSPERUS_INSTALL_PASSWORD=prueba systemd.run="/usr/bin/prosperus-instalar-disco --disco /dev/vda --si" systemd.unit=kernel-command-line.target systemd.run_success_action=poweroff systemd.run_failure_action=poweroff' \
    || true
grep -q 'PrOSperus instalado en' serie-1.log || fail 'la instalación no terminó (mira serie-1.log).'

# La entrada debe apuntar a la partición EFI del disco y a EFI/prosperus/prosperus.efi.
esp_uuid=$(sfdisk --part-uuid disco.raw 1 | tr 'A-Z' 'a-z')
grep -aiq "PrOSperus.*HD(1,GPT,$esp_uuid,.*\\\\EFI\\\\prosperus\\\\prosperus.efi" serie-1.log \
    || fail 'la entrada de arranque PrOSperus no apunta a EFI/prosperus de la partición EFI.'
num=$(grep -aoE 'Boot[0-9A-F]{4}\* PrOSperus' serie-1.log | tail -1 | cut -c5-8)
grep -a 'BootOrder:' serie-1.log | tail -1 | grep -Eq "[ ,]$num[[:space:]]*\$" \
    || fail 'PrOSperus no ha quedado al final del orden de arranque.'

echo '== Fase 2: arrancar el sistema instalado'
# OVMF descarta las entradas en forma corta HD(...) (como la de Bazzite) al
# reordenar por bootindex; el firmware real sí las usa. Aquí se arranca la misma
# imagen instalada en la EFI, con su línea de núcleo integrada.
mcopy -o -i disco.raw@@1M ::/EFI/prosperus/prosperus.efi prosperus.efi
qemu 6m -kernel prosperus.efi -drive file=disco.raw,format=raw,if=virtio \
    -serial file:serie-2.log -qmp unix:/o/qmp.sock,server=on,wait=off &
vm=$!
ok=0
for _ in $(seq 90); do
    sleep 4
    if grep -q 'PROSPERUS_READY' serie-2.log 2>/dev/null; then ok=1; break; fi
done
sleep 15
python3 - <<'PY'
import json, socket, struct, zlib
s = socket.socket(socket.AF_UNIX); s.connect('/o/qmp.sock'); f = s.makefile('rwb', buffering=0)
f.readline()
for cmd in ({'execute': 'qmp_capabilities'}, {'execute': 'screendump', 'arguments': {'filename': '/o/escritorio.ppm'}}):
    f.write(json.dumps(cmd).encode() + b'\n')
    while b'return' not in (line := f.readline()) and b'error' not in line: pass
f.write(b'{"execute": "quit"}\n')
data = open('/o/escritorio.ppm', 'rb').read()
parts = data.split(b'\n', 3); w, h = map(int, parts[1].split()); px = parts[3]
raw = b''.join(b'\0' + px[y * w * 3:(y + 1) * w * 3] for y in range(h))
chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
open('/o/escritorio.png', 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
PY
wait "$vm" || true
[ "$ok" = 1 ] || fail 'el sistema instalado no llegó al escritorio (mira serie-2.log y escritorio.png).'

echo '== Fase 3: particiones existentes intactas'
sfdisk --dump disco.raw | grep '^disco' > tabla-despues.txt
grep -vxF -f tabla-despues.txt tabla-antes.txt && fail 'una partición existente ha cambiado.'
# La EFI cambia a propósito (EFI/prosperus); xboot y «bazzite» deben ser idénticas byte a byte.
sums > sumas-despues.txt
[ "$(tail -2 sumas-antes.txt)" = "$(tail -2 sumas-despues.txt)" ] || fail 'el contenido de xboot o bazzite ha cambiado.'
mcopy -o -i disco.raw@@1M ::/EFI/fedora/shimx64.efi shim-despues.efi
[ "$(sha256sum < shimx64.efi)" = "$(sha256sum < shim-despues.efi)" ] || fail 'el cargador de «Bazzite» en la EFI ha cambiado.'
mdir -/ -b -i disco.raw@@1M ::/EFI
grep 'Boot' serie-1.log | tail -8
echo 'PRUEBA SUPERADA: instala, arranca y no toca lo existente.'
EOF
