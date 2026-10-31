#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p out/logs out/boot out/screenshots
podman build -f image/Containerfile.tools -t localhost/prosperus-tools:dev . 2>&1 | tee out/logs/tools-build.log
podman build -f image/Containerfile.base -t localhost/prosperus-base:dev . 2>&1 | tee out/logs/base-build.log
podman build -f image/Containerfile -t localhost/prosperus:dev . 2>&1 | tee out/logs/image-build.log
bash scripts/export-image.sh

# Asegurar que el disco qcow2 esté disponible y preparado para Boxes
mkdir -p out/boxes
if [[ ! -f out/prosperus.qcow2 ]]; then
    echo 'Error: out/prosperus.qcow2 no se generó. Revisa los logs en out/logs/' >&2
    exit 1
fi

# Copiar con nombre claro para importación en GNOME Boxes
cp out/prosperus.qcow2 out/boxes/prosperus-boxes.qcow2

# Verificar que la imagen sea válida (solo si qemu-img está instalado)
if command -v qemu-img >/dev/null 2>&1; then
    if ! qemu-img info --output=json out/prosperus.qcow2 > /dev/null 2>&1; then
        echo 'Error: La imagen qcow2 no es válida.' >&2
        exit 1
    fi
else
    echo 'Nota: qemu-img no está disponible en este sistema.'
fi

echo "Nota: Si prefieres usar QEMU/KVM directamente:"
echo "  bash scripts/run-vm.sh"
echo ""

echo ""
echo "=== IMAGEN LISTA PARA BOXES ==="
echo "Archivo: out/boxes/prosperus-boxes.qcow2"
echo ""
echo "Para cargar en GNOME Boxes:"
echo "  1. Abre Boxes -> '+' (Nueva máquina virtual)"
echo "  2. Selecciona 'Usar una imagen existente'"
echo "  3. Elige: $(pwd)/out/boxes/prosperus-boxes.qcow2"
echo "  4. Configura RAM (recomendado: 2 GiB) y CPU (2)"
echo "  5. Activa UEFI en la configuración avanzada de la VM"
echo ""
