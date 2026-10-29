#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Runs inside the unprivileged tools container. Never accepts a host device.
set -euo pipefail
mkdir -p /tmp/prosperus-root /output/boot
tar --numeric-owner -xf /output/rootfs.tar -C /tmp/prosperus-root
rm -f /tmp/prosperus-root/run/.containerenv /tmp/prosperus-root/.dockerenv
truncate -s 0 /tmp/prosperus-root/etc/machine-id
cp /tmp/prosperus-root/boot/vmlinuz-prosperus /output/boot/vmlinuz
cp /tmp/prosperus-root/boot/initramfs-prosperus.img /output/boot/initramfs.img
truncate -s 6G /output/rootfs.raw
mkfs.ext4 -F -L prosperus-root -d /tmp/prosperus-root /output/rootfs.raw
bash /make-uefi.sh
