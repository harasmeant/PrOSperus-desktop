# Comandos finales (montar / testear)
# SPDX-License-Identifier: GPL-3.0-only

## Montar (UEFI + disco persistente)
qemu-system-x86_64 \
  -machine q35,accel=kvm -cpu host -m 2048 -smp 2 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=/tmp/my_nvram.fd \
  -drive file="$PWD/out/boxes/prosperus-boxes.qcow2",format=qcow2,if=virtio \
  -display gtk -vga virtio -device virtio-keyboard -device virtio-mouse \
  -netdev user,id=net0 -device virtio-net-pci,netdev=net0

## Testear rápido (sin reiniciar VM, usar disco existente)
bash scripts/run-vm.sh
# O con QEMU directo:
qemu-system-x86_64 \
  -machine q35,accel=kvm -cpu host -m 2048 -smp 2 \
  -bios /usr/share/edk2/ovmf/OVMF_CODE.fd \
  -drive file="$PWD/out/prosperus.qcow2",format=qcow2,if=virtio \
  -vnc 127.0.0.1:5902 -display none -nic none
