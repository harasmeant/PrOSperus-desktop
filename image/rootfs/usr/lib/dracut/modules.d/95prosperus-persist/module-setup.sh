#!/usr/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
# Sistema persistente: la capa de cambios del Live (overlayfs) va a PROSPERUS_DATA.

check() {
    return 255  # solo si se pide con --add
}

depends() {
    echo dmsquash-live systemd
}

installkernel() {
    hostonly="" instmods ext4 loop
}

install() {
    inst_multiple blkid losetup mount umount fsck.ext4 e2fsck df awk sleep rm rmdir ln mkdir cat basename readlink
    inst_script "$moddir/prosperus-persist.sh" /usr/bin/prosperus-persist
    inst_simple "$moddir/prosperus-persist.service" "$systemdsystemunitdir/prosperus-persist.service"
    $SYSTEMCTL -q --root "$initdir" add-wants initrd.target prosperus-persist.service
}
