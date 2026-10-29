#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
cd "$(dirname "$0")/.."
test -f out/prosperus.qcow2 && test -f out/boot/vmlinuz && test -f out/boot/initramfs.img
test -r /dev/kvm && test -w /dev/kvm || { echo 'KVM access is required.' >&2; exit 1; }
mkdir -p out/vm
if podman container exists prosperus-vm; then
    echo 'A prosperus-vm container already exists. Inspect or stop it first.' >&2
    exit 1
fi
rm -f out/vm/qmp.sock
# No host disks, home directory, clipboard, network card or USB are given to the guest.
# VNC is forwarded only to the host loopback address. QMP is a local Unix socket.
podman run --rm --name prosperus-vm --device /dev/kvm \
    --security-opt label=disable -p 127.0.0.1:5902:5900 \
    -v "$PWD/out:/output" localhost/prosperus-tools:dev \
    qemu-system-x86_64 -machine q35,accel=kvm -cpu host -smp 2 -m 2048 \
    -kernel /output/boot/vmlinuz -initrd /output/boot/initramfs.img \
    -append 'root=LABEL=prosperus-root rootfstype=ext4 rw console=tty0 console=ttyS0,115200 selinux=0 systemd.show_status=1' \
    -drive file=/output/prosperus.qcow2,format=qcow2,if=virtio,snapshot=on \
    -device virtio-vga -device virtio-keyboard-pci -device virtio-mouse-pci \
    -display none -vnc 0.0.0.0:0 -nic none \
    -serial file:/output/vm/serial.log \
    -qmp unix:/output/vm/qmp.sock,server=on,wait=off
