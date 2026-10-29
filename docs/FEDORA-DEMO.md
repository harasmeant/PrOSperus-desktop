# Probar el escritorio independiente en Fedora

## Preparar el paquete en el repositorio

```bash
python3 scripts/package-fedora-demo.py
```

Produce `out/prosperus-demo-v3.2.tar.gz` y su suma SHA-256. Solo incluye el código
independiente, los ejemplos de `demo-system/`, los fondos identificados en
`DEMO-ASSETS.md`, la licencia y el lanzador. No necesita compilar una imagen.

## Dentro de Fedora

Transfiere el archivo a la VM de Boxes y extráelo. Entra en `prosperus-demo-v3.2`,
la carpeta que contiene `iniciar.sh`, y abre una terminal allí:

```bash
sh iniciar.sh
```

No hay que entrar en la subcarpeta `prosperus/`. El lanzador resuelve sus propias
rutas; también se puede ejecutar indicando la ruta completa de `iniciar.sh`.
Si las dependencias ya están presentes, basta con ejecutar el lanzador.
Desde v3.2, `iniciar.sh` también detecta el entorno ligero preparado en
`/tmp/prosperus-runtime`: verifica su propietario y que puede importar Qt antes
de reutilizarlo. No hace falta elegir un lanzador diferente para Fedora Live.
Si faltan dependencias en el Live, sigue la alternativa ligera de esta guía.
En Fedora instalado con espacio suficiente puedes usar
`sudo dnf install --setopt=install_weak_deps=False python3-pyside6 qt6-qtwayland python3-gobject`.

## Si DNF pide más espacio en `/`

La sesión Live puede tener un área de escritura pequeña, independiente del
tamaño del disco virtual. En la prueba de v0.3 se observó un `LiveOS_rootfs`
de 777 MiB, con 183 MiB disponibles, mientras `/tmp` tenía 1.9 GiB libres.
DNF abortó la transacción pidiendo unos 387 MB adicionales: la aplicación no
llegó a disponer de PySide6. No es una prueba de arranque de v0.3 completada.

Ejecuta cada comprobación por separado:

```bash
df -h / /var/cache /tmp
```

```bash
sudo du -sh /var/cache/libdnf5
```

El [paquete PySide6 de Fedora](https://packages.fedoraproject.org/pkgs/python-pyside6/python3-pyside6/fedora-44.html)
depende de varios módulos Qt, incluido WebEngine, aunque esta interfaz no lo
use. Desactivar dependencias débiles no elimina esas dependencias obligatorias.
DNF5 permite cambiar la caché de root con
[`system_cachedir`](https://dnf5.readthedocs.io/en/latest/misc/caching.7.html).
Mover una caché existente a un `/tmp` separado puede liberar espacio en `/`,
pero hay que comprobar su tamaño y el espacio necesario para instalar.
Cambiar solo la ruta de caché no retira las descargas anteriores ni amplía `/`.

Si no cabe la instalación, la alternativa duradera es Fedora instalado en el
disco de la VM. Guarda tus notas fuera de la sesión Live antes de cerrarla.
El lanzador 0.3.1 muestra el error concreto de importación y el espacio libre;
no modifica particiones, cachés ni paquetes por su cuenta.

### Alternativa con los módulos básicos de Qt en `/tmp`

Si `/tmp` tiene espacio libre, [Qt distribuye PySide6 Essentials por separado](https://doc.qt.io/qtforpython-6/package_details.html).
Incluye los módulos usados por esta interfaz y sus bibliotecas Qt, sin instalar
el paquete completo de Fedora en `/`. Ejecuta estas líneas una a una:

```bash
python3 -m venv --system-site-packages /tmp/prosperus-runtime
```

```bash
/tmp/prosperus-runtime/bin/python -m pip install --no-cache-dir --only-binary=:all: PySide6-Essentials
```

Desde la carpeta extraída de v3.2:

```bash
sh iniciar.sh
```

Si ambas carpetas están juntas en Descargas, puedes usar directamente los
proyectos que ya importaste o editaste en v3:

```bash
sh iniciar.sh --root ../prosperus-demo-v3/proyectos
```

Para la v3 anterior, que no incluye ese lanzador, desde su carpeta extraída:

```bash
/tmp/prosperus-runtime/bin/python -m prosperus --root ./proyectos
```

La preparación requiere Internet y se repite después de reiniciar: el entorno
de `/tmp` es temporal. Las notas se guardan en `proyectos/`, no en el entorno
Python. Se conserva el acceso a GIO instalado por Fedora para Aplicaciones.
Las bibliotecas gráficas del sistema y la sesión Wayland/X11 siguen siendo
necesarias. No ejecutar `sudo pip` ni instalar todo `PySide6` en ese entorno.

## Comprobar la experiencia

1. Haz doble clic en Bienvenida y compara sus ocho tarjetas y su fondo con la demo de Obsidian.
2. Abre Carpetas. Recorre portadas con la rueda/flechas: el escritorio no cambia
   hasta pulsar la portada o Intro. Prueba el filtro, Fijar y el borde izquierdo.
3. Abre Laboratorio y entra en Apuntes: conserva el wallpaper y la paleta azul.
4. Abre dos notas. Mueve, redimensiona, minimiza y recupera; cambia de proyecto
   y vuelve para comprobar las ventanas de cada carpeta.
5. En una nota de ejemplo, pulsa Editar, escribe Markdown, guarda con Ctrl+S y
   vuelve a Vista previa. Cierra y abre la nota para comprobar el archivo.
6. Pulsa Nuevo proyecto, ponle nombre y crea una nota. Usa Ctrl+Mayús+N para
   crear una carpeta. En el mapa un clic selecciona y doble clic o Intro abre.
7. Abre Aplicaciones, busca una herramienta instalada, fíjala y ábrela. El
   programa utiliza sus permisos normales dentro de Fedora; esto no prueba
   aislamiento de aplicaciones por proyecto.
8. Selecciona una nota y pulsa Ctrl+C. Entra en otra carpeta y pulsa Ctrl+V.
   Ctrl+D duplica lo seleccionado. Ctrl+clic selecciona varios; el menú de clic
   derecho permite las mismas acciones. Las copias usan los cambios guardados.
9. En Carpetas, pulsa Importar proyecto para copiar una carpeta externa. También
   puedes copiar en Archivos de Fedora y pegar en PrOSperus, o arrastrar al mapa.
   Los originales se conservan. Un nombre repetido añade ` - copia`; la copia
   no sigue enlaces simbólicos ni reescribe enlaces Markdown entre carpetas.
10. Prueba Ctrl+Espacio, F1, F5, F11, Alt+↑ y Alt+←/→. Los atajos de texto
    mantienen su función habitual dentro del editor.
11. Escribe una palabra en el cuerpo de una nota y guárdala. Búscala desde el
    mapa y Explorar: aparece aunque no forme parte del nombre. Carpetas también
    encuentra su proyecto por ese contenido. La búsqueda recorre subcarpetas,
    ignora tildes/mayúsculas y exige todos los términos dentro del nombre/ruta
    o contenido de una misma nota. Busca la versión guardada; los Markdown
    ilegibles o mayores de 2 MiB solo pueden coincidir por nombre/ruta.

## Tecla Windows y controles de sesión

La [tecla Super abre Actividades en GNOME](https://help.gnome.org/gnome-help/keyboard-key-super.html).
La demo recibe solo los eventos que Fedora le entrega; pantalla completa no
convierte PrOSperus en el gestor global de teclado o ventanas. Usa Ctrl+Espacio
para Aplicaciones en esta prueba. El manejador de Super, Super+E, Super+D y
Super+I está implementado para cuando la sesión le entregue esos eventos.
Alt+Tab y la gestión global de ventanas siguen perteneciendo al compositor.

El botón Controles utiliza [wpctl](https://pipewire.pages.freedesktop.org/wireplumber/man/wpctl.html),
[playerctl](https://github.com/altdesktop/playerctl) y
[brightnessctl](https://github.com/Hummer12007/brightnessctl). Se pueden instalar
opcionalmente en Fedora con `sudo dnf install wireplumber playerctl brightnessctl`.
Los controles actúan en el sistema donde ejecutas la aplicación: en la VM, en
la VM. Volumen requiere una sesión de audio activa; reproducción, un reproductor
MPRIS; brillo, una pantalla con retroiluminación expuesta al sistema. Los botones
se desactivan si falta la herramienta o, para brillo, el dispositivo. Los errores
de sesión/permisos se muestran en el panel. Fn depende del propio teclado.

La receta de imagen sigue siendo experimental; no se ha reconstruido con estos
cambios y requiere completar la integración global y de audio.

Los cambios se guardan en los Markdown de la demo. En Fedora Live, copia fuera
de la sesión los archivos que quieras conservar antes de apagar. Conserva la
demo anterior por separado si has escrito notas en ella.

## Validación local

```bash
PYTHONPATH=desktop QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests
PYTHONPATH=desktop QT_QPA_PLATFORM=offscreen python3 -m prosperus --root demo-system --screenshot out/preview.png
```

Las pruebas usan carpetas temporales para las escrituras y simulan el lanzamiento
de aplicaciones. No necesitan la VM ni abren programas del anfitrión. La captura
sin pantalla verifica el renderizado de Qt, no el comportamiento del compositor
Wayland de Fedora ni su integración con Boxes.
