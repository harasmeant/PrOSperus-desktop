#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
cd "$(dirname "$0")/.."
# Arch: PROSPERUS_ISO_DIR=out/iso-arch PROSPERUS_TOOLS=localhost/prosperus-arch-tools:dev
#       PROSPERUS_VM_NAME=prosperus-arch-vm PROSPERUS_VNC_PORT=5904 (puede convivir con la de Fedora)
# Debian: lo mismo con iso-debian, prosperus-debian-tools:dev, prosperus-debian-vm y 5905.
iso_dir=${PROSPERUS_ISO_DIR:-out/iso}
tools=${PROSPERUS_TOOLS:-localhost/prosperus-live-tools:dev}
name=${PROSPERUS_VM_NAME:-prosperus-iso-vm}
port=${PROSPERUS_VNC_PORT:-5903}
test -f "$iso_dir/prosperus-live-x86_64.iso"
test -r /dev/kvm && test -w /dev/kvm
memory=${PROSPERUS_VM_MEMORY_MB:-2048}
if [[ ! "$memory" =~ ^[0-9]+$ ]] || (( memory < 1024 || memory > 4096 )); then
    echo 'PROSPERUS_VM_MEMORY_MB debe estar entre 1024 y 4096.' >&2
    exit 1
fi
# Dejar margen al anfitrión y limitar también QEMU, sin permitirle usar swap.
available=$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
if (( available < memory + 1024 )); then
    echo 'Falta RAM disponible. Guarda las notas y cierra otras VM antes de probar.' >&2
    exit 1
fi
if podman container exists "$name"; then
    echo 'La VM de prueba ya existe; revísala antes de iniciar otra.' >&2
    exit 1
fi
mkdir -p "$iso_dir/screenshots" "$iso_dir/vm"
# Fresh firmware variables keep each test independent of saved boot entries.
podman run --rm --network=none --security-opt label=disable \
    -v "$PWD/$iso_dir:/output" "$tools" \
    cp /usr/share/edk2/ovmf/OVMF_VARS.fd /output/vm/OVMF_VARS.fd
# Boot the optical medium through firmware, without -kernel or a virtual disk.
# No host disks, shared projects, network card or USB are exposed to this guest.
podman run --rm --name "$name" --device /dev/kvm \
    --cpus=2 --memory="$((memory + 256))m" --memory-swap="$((memory + 256))m" \
    --security-opt label=disable -p "127.0.0.1:$port:5900" \
    -v "$PWD/$iso_dir:/output" "$tools" \
    qemu-system-x86_64 -machine q35,accel=kvm -cpu host -smp 2 -m "$memory" \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
    -drive if=pflash,format=raw,file=/output/vm/OVMF_VARS.fd \
    -cdrom /output/prosperus-live-x86_64.iso -boot order=d \
    -device virtio-vga -device virtio-keyboard-pci -device virtio-mouse-pci \
    -display none -vnc 0.0.0.0:0 -nic none \
    -serial file:/output/vm/serial.log \
    -qmp unix:/output/vm/qmp.sock,server=on,wait=off
