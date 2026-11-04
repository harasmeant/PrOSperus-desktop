#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# ISO Live de PrOSperus sobre Arch Linux. Resultado en out/iso-arch/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out/iso-arch
limits=(--cpu-period=100000 --cpu-quota=200000 --memory=2g --memory-swap=2g)
podman build "${limits[@]}" -f image/arch/Containerfile.tools -t localhost/prosperus-arch-tools:dev .
podman build "${limits[@]}" -f image/arch/Containerfile.base -t localhost/prosperus-arch-base:dev .
podman build "${limits[@]}" -f image/arch/Containerfile -t localhost/prosperus-arch:dev .
podman build "${limits[@]}" -f image/arch/Containerfile.live -t localhost/prosperus-arch-live:dev .
container=$(podman create localhost/prosperus-arch-live:dev)
trap 'podman rm "$container" >/dev/null' EXIT
podman export -o out/iso-arch/rootfs-live.tar "$container"
podman run --rm --network=none --cpus=2 --memory=1g --memory-swap=1g \
    --security-opt label=disable -v "$PWD/out/iso-arch:/output" \
    -v "$PWD/scripts:/scripts:ro" localhost/prosperus-arch-tools:dev \
    bash /scripts/make-iso.sh
rm -f out/iso-arch/rootfs-live.tar
echo "ISO lista: out/iso-arch/prosperus-live-x86_64.iso"
echo "Probarla: PROSPERUS_ISO_DIR=out/iso-arch PROSPERUS_TOOLS=localhost/prosperus-arch-tools:dev bash scripts/run-iso.sh"
