#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# ISO Live de PrOSperus sobre Debian 13 (trixie). Resultado en out/iso-debian/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out/iso-debian
limits=(--cpu-period=100000 --cpu-quota=200000 --memory=2g --memory-swap=2g)
podman build "${limits[@]}" -f image/debian/Containerfile.tools -t localhost/prosperus-debian-tools:dev .
podman build "${limits[@]}" -f image/debian/Containerfile.base -t localhost/prosperus-debian-base:dev .
podman build "${limits[@]}" -f image/debian/Containerfile -t localhost/prosperus-debian:dev .
podman build "${limits[@]}" -f image/debian/Containerfile.live -t localhost/prosperus-debian-live:dev .
container=$(podman create localhost/prosperus-debian-live:dev)
trap 'podman rm "$container" >/dev/null' EXIT
podman export -o out/iso-debian/rootfs-live.tar "$container"
podman run --rm --network=none --cpus=2 --memory=1g --memory-swap=1g \
    --security-opt label=disable -v "$PWD/out/iso-debian:/output" \
    -v "$PWD/scripts:/scripts:ro" localhost/prosperus-debian-tools:dev \
    bash /scripts/make-iso.sh
rm -f out/iso-debian/rootfs-live.tar
echo "ISO lista: out/iso-debian/prosperus-live-x86_64.iso"
echo "Probarla: PROSPERUS_ISO_DIR=out/iso-debian PROSPERUS_TOOLS=localhost/prosperus-debian-tools:dev PROSPERUS_VM_NAME=prosperus-debian-vm PROSPERUS_VNC_PORT=5905 bash scripts/run-iso.sh"
