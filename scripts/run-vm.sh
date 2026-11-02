#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
cd "$(dirname "$0")/.."
test -f out/prosperus.qcow2 && test -f out/boot/vmlinuz && test -f out/boot/initramfs.img
test -r /dev/kvm && test -w /dev/kvm || { echo 'KVM access is required.' >&2; exit 1; }
mkdir -p out/vm

qemu-system-x86_64 -machine q35,accel=kvm -cpu host -smp 2 -m 2048 \
    -kernel out/boot/vmlinuz -initrd out/boot/initramfs.img \
    -append 'root=LABEL=prosperus-root rootfstype=ext4 rw console=tty0 console=ttyS0,115200 selinux=0 systemd.show_status=1 video=1024x768' \
    -drive file=out/prosperus.qcow2,format=qcow2,if=virtio,snapshot=on \
    -vga virtio -usb -device usb-tablet -device virtio-keyboard-pci \
    -netdev user,id=net0 \
    -device virtio-net-pci,netdev=net0 \
    -display gtk \
    -serial file:out/vm/serial.log
