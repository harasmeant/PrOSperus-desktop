#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
set -eu
cd -- "$(dirname -- "$0")"

if [ -n "${PROSPERUS_PYTHON:-}" ]; then
    prosperus_python=$PROSPERUS_PYTHON
else
    prosperus_python=/usr/bin/python3
    if ! "$prosperus_python" -c 'from PySide6.QtWidgets import QApplication' >/dev/null 2>&1; then
        prosperus_runtime=/tmp/prosperus-runtime
        # Only reuse an environment belonging to the user launching the app.
        if [ -d "$prosperus_runtime" ] &&
           [ "$(stat -c %u -- "$prosperus_runtime")" = "$(id -u)" ] &&
           [ -x "$prosperus_runtime/bin/python" ] &&
           "$prosperus_runtime/bin/python" -c 'from PySide6.QtWidgets import QApplication' >/dev/null 2>&1; then
            prosperus_python=$prosperus_runtime/bin/python
            printf '%s\n' 'Usando el entorno ligero de PrOSperus.'
        fi
    fi
fi

exec "$prosperus_python" -m prosperus.bootstrap --root "$PWD/proyectos" "$@"
