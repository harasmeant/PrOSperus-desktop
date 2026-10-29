#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Runs inside the tools container. All outputs are regular files, never devices.
set -euo pipefail
work=$(mktemp -d /output/iso-build.XXXXXX)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/root" "$work/tree/LiveOS" "$work/tree/EFI"
tar -xf /output/rootfs-live.tar -C "$work/root"
rm -f "$work/root/run/.containerenv" "$work/root/.dockerenv"
truncate -s 0 "$work/root/etc/machine-id"

# Read the compressed root directly from the CD. Only changes occupy guest RAM;
# rd.live.ram would copy the entire image and unnecessarily increase RAM usage.
ukify build --linux="$work/root/boot/vmlinuz-prosperus" \
    --initrd="$work/root/boot/initramfs-prosperus.img" \
    --cmdline='root=live:CDLABEL=PROSPERUS_LIVE rd.live.image rd.live.overlay.overlayfs=1 rw console=tty0 console=ttyS0,115200 selinux=0 systemd.show_status=1' \
    --os-release="@$work/root/etc/os-release" --output="$work/BOOTX64.EFI"
truncate -s 128M "$work/tree/EFI/efiboot.img"
mkfs.vfat -F 32 -n PROSPERUS "$work/tree/EFI/efiboot.img"
mmd -i "$work/tree/EFI/efiboot.img" ::/EFI ::/EFI/BOOT
mcopy -i "$work/tree/EFI/efiboot.img" "$work/BOOTX64.EFI" ::/EFI/BOOT/BOOTX64.EFI

# Limit compression workers and buffers on hosts also running a Fedora VM.
mksquashfs "$work/root" "$work/tree/LiveOS/squashfs.img" \
    -noappend -comp zstd -processors 2 -mem 256M -no-progress
# Keep the FAT inside the ISO volume. With an appended image larger than 32 MiB,
# OVMF can calculate an empty El Torito partition from the ISO volume boundary.
xorriso -as mkisofs -V PROSPERUS_LIVE -R -J -no-pad \
    -efi-boot-part --efi-boot-image \
    -e EFI/efiboot.img -no-emul-boot \
    -o /output/prosperus-live-x86_64.iso "$work/tree"
xorriso -indev /output/prosperus-live-x86_64.iso -report_el_torito plain \
    > /output/boot-catalog.txt 2>&1
cp "$work/root/usr/share/prosperus/packages.txt" /output/packages.txt
cd /output
sha256sum prosperus-live-x86_64.iso > prosperus-live-x86_64.iso.sha256
