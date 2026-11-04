"""Desktop-like shortcuts without taking clipboard keys away from text editors."""
# SPDX-License-Identifier: GPL-3.0-only
from PySide6.QtCore import QEvent, QObject, QTimer, Qt, Slot
from PySide6.QtWidgets import QApplication

SHORTCUT_HELP = '''# Manejar PrOSperus

## Proyectos y archivos
- **Ctrl+Alt+N:** nuevo proyecto, siempre en Tus proyectos.
- **Ctrl+N:** nueva nota. **Ctrl+Mayús+N:** nueva carpeta.
- Un clic selecciona; **Ctrl+clic** amplía la selección; doble clic o **Intro** abre.
- **Ctrl+C / Ctrl+V:** copiar / pegar carpetas y notas; también desde Archivos de Fedora.
- **Ctrl+D:** duplicar. **Ctrl+A:** seleccionar los elementos de la página del mapa o la lista del explorador.
- Clic derecho: copiar, duplicar, pegar e importar. Arrastra archivos locales al mapa para copiarlos; sobre una carpeta se copian dentro de ella.
- Las copias conservan los originales. Un nombre repetido añade « - copia»; no se sobrescribe.

## Navegación y ventanas
- **Esc / Alt+↑ / Retroceso:** volver a la carpeta anterior (Retroceso con el mapa o la lista enfocados; Esc cierra antes la nota enfocada).
- **Alt+← / Alt+→:** historial del mapa. **Ctrl+Inicio:** todos los proyectos.
- **Ctrl+B:** tarjetero. **Ctrl+1…9:** abrir un proyecto por su posición.
- **Ctrl+F / Ctrl+L:** buscar notas (en el explorador, buscar en su carpeta).
- **Ctrl+O:** abrir la primera nota del proyecto.
- **Ctrl+S:** guardar la nota enfocada. **Ctrl+W:** cerrar la nota enfocada.
- **Esc:** recoger el tarjetero, cerrar la nota enfocada o volver a la carpeta anterior; en el explorador sube una carpeta y, arriba del todo, lo cierra.
- **Ctrl+Tab / Ctrl+Mayús+Tab:** siguiente/anterior nota abierta del proyecto.
- **Flechas:** en el mapa, seleccionar la carpeta o nota más cercana en esa dirección. **Intro** abre. **Tab / Mayús+Tab:** siguiente/anterior control. **Espacio** activa el botón enfocado.
- **Super+Tab / Super+Mayús+Tab:** pasar al proyecto siguiente/anterior, también con una aplicación delante.
- **Mayús+F10 / Menú:** menú contextual del mapa o de la lista de archivos.
- **F1:** esta ayuda. **F5 / Ctrl+R:** actualizar. **F11:** pantalla completa.
- **Alt+F4:** cerrar la ventana, con confirmación si hay notas sin guardar.
- **Ctrl+I:** información del sistema (versión, autor, licencia).

## Aplicaciones y controles
- **Windows / Super:** abrir o cerrar Aplicaciones, cuando el sistema entrega esa tecla a PrOSperus.
- **Ctrl+Espacio / Alt+F2:** Aplicaciones (Alt+F2 puede estar reservado por el sistema).
- **Super+E:** explorador. **Super+D:** ocultar/restaurar notas y aplicaciones del proyecto. **Super+↑:** ampliar o restaurar la aplicación. **Super+↓ / Super+M:** minimizarla. **Super+F:** pantalla completa de la aplicación. **Alt+F4 / Super+Q:** cerrar la aplicación. **Super+Esc:** volver al escritorio. **Super+I:** controles.
- **Mover y redimensionar aplicaciones:** arrastra su barra de título, o **Super+arrastrar** (mover) y **Super+clic derecho+arrastrar** (tamaño) desde cualquier punto. **Super+Alt+flechas:** ensanchar/estrechar y alargar/acortar la ventana enfocada.
- **Hueco entre aplicaciones:** arrastrarlo mueve ese borde en todas las ventanas que lo comparten (como un separador). **Doble clic en el fondo del escritorio:** minimiza las aplicaciones del proyecto (Super+D las devuelve). Al abrir o cerrar una aplicación, Fibonacci vuelve a repartirlas.
- Las teclas de volumen, brillo y reproducción se atienden en la sesión propia PrOSperus cuando están disponibles.

## Texto y accesibilidad
- **Ctrl+X / Ctrl+C / Ctrl+V / Ctrl+A:** cortar, copiar, pegar y seleccionar texto.
- **Ctrl+Z / Ctrl+Mayús+Z / Ctrl+Y:** deshacer / rehacer en el editor.
- **Ctrl+← / Ctrl+→:** palabra anterior/siguiente; **Mayús** amplía la selección.
- **Inicio / Fin / Ctrl+Inicio / Ctrl+Fin:** principio/final de línea o documento en el editor.
- **Controles → Accesibilidad y botones:** texto al 100/125/150 %, botones grandes, alto contraste y clic simple opcional. Por defecto, un clic selecciona y doble clic abre; con clic simple, Ctrl+clic selecciona sin abrir.
- **Controles → Hardware y drivers:** consultar los dispositivos PCI y su controlador asociado.

En esta demo dentro de GNOME, Windows/Super, Alt+Tab, Super+L (bloqueo), Impr Pant y otros atajos globales los gestiona Fedora. F11 no cambia esto. No hay todavía implementación propia de bloqueo, captura, terminal global ni cambio de aplicaciones en la ISO. F2, Supr y Ctrl+X sobre archivos quedan pendientes de renombrado, papelera y movimiento con protección de enlaces. Los controles de brillo requieren hardware compatible; una VM normalmente no lo ofrece. La tecla Fn depende del teclado.

Dentro de un editor, Ctrl+C, Ctrl+V y Ctrl+A actúan sobre el texto. Copiar una nota copia su última versión guardada. La copia conserva los enlaces tal como están escritos: no los reescribe al cambiar de carpeta.
'''


# Filtro de eventos global para atajos de escritorio sin robar Ctrl+C/V a editores de texto.
class DesktopKeys(QObject):
    def __init__(self, shell):
        # Instala el filtro de eventos y se desconecta al destruir la shell.
        super().__init__(shell)
        self.shell = shell
        self.super_pressed = False
        self.cycling = False
        self.super_combination = False
        QApplication.instance().installEventFilter(self)
        shell.destroyed.connect(self.detach)

    @Slot()
    def detach(self):
        # Elimina el filtro de eventos cuando la shell se destruye.
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, target, event):
        # Intercepta teclas para atajos de escritorio antes de que lleguen a los widgets.
        if event.type() == QEvent.Type.ApplicationDeactivate:
            # Al perder el foco se reinicia Super para evitar atajos fantasma.
            self.super_pressed = False
            return False
        if event.type() == QEvent.Type.Show:
            # Los diálogos del escritorio se visten con el marco del proyecto al aparecer.
            self.shell.frame_dialogs(target, event)
            return False
        if event.type() not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.ShortcutOverride):
            return False
        if not self.shell.isVisible():
            return False
        if not hasattr(target, 'window'):
            return False
        owner = target
        # Sube por el árbol de widgets hasta encontrar la shell principal; ignora ventanas ajenas.
        while owner is not None and owner != self.shell:
            owner = owner.parent()
        if owner is None:
            return False
        key = event.key()
        # Cualquier tecla distinta de Meta mientras Super está pulsada marca una combinación.
        if key != Qt.Key.Key_Meta and self.super_pressed:
            self.super_combination = True
        if event.type() == QEvent.Type.ShortcutOverride:
            # No interceptar ShortcutOverride: dejar que Qt gestione los atajos estándar.
            return False
        if key == Qt.Key.Key_Meta:
            # Abrir al soltar Super, solo si no formó una combinación: Super+E
            # debe abrir el explorador sin abrir además el panel de aplicaciones.
            if event.isAutoRepeat():
                return True
            if event.type() == QEvent.Type.KeyPress:
                self.super_pressed = True; self.super_combination = False
            elif self.super_pressed:
                self.super_pressed = False
                if self.cycling:
                    # Como Alt+Tab: al soltar Super se abre el proyecto elegido.
                    self.cycling = False
                    QTimer.singleShot(0, self.shell.drawer.open_current)
                elif self.shell.system_session:
                    # En Sway, Super sola la decide Sway (--release): aquí no se sabe si Sway
                    # se quedó la otra tecla (Super+Intro abría la terminal y además Buscar).
                    pass
                elif not self.super_combination and QApplication.activeModalWidget() is None:
                    QTimer.singleShot(0, self.shell.toggle_applications)
            return True
        if event.type() != QEvent.Type.KeyPress:
            # El resto solo procesa pulsaciones, no sueltas.
            return False
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            # Super+Tab baja por los proyectos; Super+Mayús+Tab sube.
            drawer = self.shell.drawer
            if not drawer.isVisible():
                drawer.reveal()
            drawer.step(-1 if key == Qt.Key.Key_Backtab or event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1)
            self.cycling = True
            # Marca ciclado para que al soltar Super se abra el proyecto elegido.
            return True
        # GNOME/KDE remain responsible for global hardware keys in window mode.
        if self.shell.system_session and self.shell.controls.handle_key(key):
            return True
        context = self.shell.file_context(target)
        # Obtiene carpeta, rutas y acciones de contexto del widget objetivo.
        if context is None:
            return False
        folder, paths, select_all, go_up = context
        modifiers = event.modifiers()
        if ((modifiers == Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_F10)
                or (modifiers == Qt.KeyboardModifier.NoModifier and key == Qt.Key.Key_Menu)):
            # Menú contextual con Shift+F10 o tecla Menú.
            from PySide6.QtWidgets import QListWidget
            if isinstance(target, QListWidget):
                rect = target.visualItemRect(target.currentItem()) if target.currentItem() else target.viewport().rect()
                target.window().context_menu(rect.center())
            else:
                self.shell.surface.show_menu(target.mapToGlobal(target.rect().center()))
            return True
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            # Atajos de Control sobre archivos: copiar, pegar, duplicar, seleccionar todo.
            if key == Qt.Key.Key_C:
                self.shell.files.copy(paths); return True
            if key == Qt.Key.Key_V:
                self.shell.files.paste(folder); return True
            if key == Qt.Key.Key_D:
                if paths:
                    self.shell.files.transfer(paths, folder)
                return True
            if key == Qt.Key.Key_A:
                select_all(); return True
        if modifiers == Qt.KeyboardModifier.NoModifier and key == Qt.Key.Key_F2 and len(paths) == 1:
            self.shell.rename_path(paths[0]); return True
        if modifiers == Qt.KeyboardModifier.NoModifier and key == Qt.Key.Key_Delete and paths:
            self.shell.trash_paths(paths); return True
        if modifiers == Qt.KeyboardModifier.NoModifier and key == Qt.Key.Key_Backspace:
            # Retroceso sin modificadores sube un nivel de carpeta.
            go_up(); return True
        return False
