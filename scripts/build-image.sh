#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out/logs out/boot out/screenshots
podman build -f image/Containerfile.tools -t localhost/prosperus-tools:dev . 2>&1 | tee out/logs/tools-build.log
podman build -f image/Containerfile.base -t localhost/prosperus-base:dev . 2>&1 | tee out/logs/base-build.log
podman build -f image/Containerfile -t localhost/prosperus:dev . 2>&1 | tee out/logs/image-build.log
bash scripts/export-image.sh
