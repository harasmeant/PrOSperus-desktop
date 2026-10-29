#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out/logs out/boot
if podman container exists prosperus-vm; then
    echo 'Stop the development VM before replacing its image.' >&2
    exit 1
fi
container_id=$(podman create localhost/prosperus:dev)
trap 'podman rm "$container_id" >/dev/null' EXIT
podman export -o out/rootfs.tar "$container_id"
podman run --rm --network=none --security-opt label=disable \
    -v "$PWD/out:/output" -v "$PWD/scripts/make-disk.sh:/make-disk.sh:ro" \
    -v "$PWD/scripts/make-uefi.sh:/make-uefi.sh:ro" \
    localhost/prosperus-tools:dev bash /make-disk.sh 2>&1 | tee out/logs/disk-build.log
podman image inspect localhost/prosperus:dev > out/image-inspect.json
podman run --rm --network=none localhost/prosperus:dev cat /usr/share/prosperus/packages.txt > out/packages.txt
sha256sum out/prosperus.qcow2 out/boot/vmlinuz out/boot/initramfs.img > out/SHA256SUMS
echo 'Ready: out/prosperus.qcow2 and out/boot/. Run: bash scripts/run-vm.sh'
