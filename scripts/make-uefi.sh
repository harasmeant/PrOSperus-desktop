#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Build a GPT disk with an EFI System Partition and the existing root filesystem.
# Only regular files beneath /output are written; no loop device or mount is used.
set -euo pipefail
mkdir -p /output/boot
ukify build --linux=/output/boot/vmlinuz --initrd=/output/boot/initramfs.img \
    --cmdline='root=LABEL=prosperus-root rootfstype=ext4 rw console=tty0 console=ttyS0,115200 selinux=0 systemd.show_status=1' \
    --os-release='ID=prosperus
NAME="PrOSperus desktop"
VERSION_ID=0.3.2-dev
PRETTY_NAME="PrOSperus desktop development"' \
    --output=/output/boot/BOOTX64.EFI
truncate -s 256M /output/esp.img
mkfs.vfat -F 32 -n PROSPERUS /output/esp.img
mmd -i /output/esp.img ::/EFI ::/EFI/BOOT
mcopy -o -i /output/esp.img /output/boot/BOOTX64.EFI ::/EFI/BOOT/BOOTX64.EFI
# 1 MiB alignment + 256 MiB ESP + 6 GiB root + 1 MiB backup GPT space.
truncate -s 6712983552 /output/prosperus-uefi.raw
sgdisk --clear --new=1:2048:+256M --typecode=1:ef00 --change-name=1:EFI \
    --new=2:0:+6G --typecode=2:8300 --change-name=2:PrOSperus \
    /output/prosperus-uefi.raw
dd if=/output/esp.img of=/output/prosperus-uefi.raw bs=1M seek=1 conv=notrunc,sparse status=none
dd if=/output/rootfs.raw of=/output/prosperus-uefi.raw bs=1M seek=257 conv=notrunc,sparse status=none
sgdisk --verify /output/prosperus-uefi.raw
qemu-img convert -f raw -O qcow2 /output/prosperus-uefi.raw /output/prosperus.qcow2
qemu-img check /output/prosperus.qcow2
qemu-img info --output=json /output/prosperus.qcow2 > /output/disk-info.json
