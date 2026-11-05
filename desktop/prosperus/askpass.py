# SPDX-License-Identifier: GPL-3.0-only
"""Pide la contraseña de sudo con una ventana (SUDO_ASKPASS para «sudo -A»).

sudo ejecuta este programa con el texto de la pregunta como argumento y lee la contraseña de su
salida estándar. Cancelar sale con código 1 y sudo no ejecuta nada."""
import sys

from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit

TITLE = 'Contraseña de administrador'
TEXT = 'Instalar programas necesita tu contraseña.\nEs la misma con la que desbloqueas la sesión.'


def main(argv=None):
    argv = sys.argv if argv is None else argv
    app = QApplication(argv[:1])
    app.setApplicationName('prosperus-askpass')
    app.setDesktopFileName('prosperus-askpass')
    password, ok = QInputDialog.getText(None, TITLE, TEXT, QLineEdit.EchoMode.Password)
    if not ok:
        return 1
    sys.stdout.write(password + '\n')
    sys.stdout.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
