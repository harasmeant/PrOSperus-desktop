#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out/iso
# The cached base and tools images are built with scripts/build-image.sh's
# Containerfiles. Build them here too so this recipe also works on a clean host.
limits=(--cpu-period=100000 --cpu-quota=200000 --memory=1g --memory-swap=1g)
podman build "${limits[@]}" -f image/Containerfile.tools -t localhost/prosperus-tools:dev .
podman build "${limits[@]}" -f image/Containerfile.base -t localhost/prosperus-base:dev .
podman build "${limits[@]}" -f image/Containerfile.live-tools -t localhost/prosperus-live-tools:dev .
podman build "${limits[@]}" -f image/Containerfile -t localhost/prosperus:dev .
podman build "${limits[@]}" -f image/Containerfile.live -t localhost/prosperus-live:dev .
# A unique container ID keeps cleanup separate from any running test VM.
container=$(podman create localhost/prosperus-live:dev)
trap 'podman rm "$container" >/dev/null' EXIT
podman export -o out/iso/rootfs-live.tar "$container"
podman run --rm --network=none --cpus=2 --memory=1g --memory-swap=1g \
    --security-opt label=disable -v "$PWD/out/iso:/output" \
    -v "$PWD/scripts:/scripts:ro" localhost/prosperus-live-tools:dev \
    bash /scripts/make-iso.sh
