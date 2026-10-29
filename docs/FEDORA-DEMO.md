# Probar el escritorio independiente en Fedora

## Preparar el paquete en el repositorio

```bash
python3 scripts/package-fedora-demo.py
```

Produce `out/prosperus-demo-v2.tar.gz` y su suma SHA-256. Solo incluye el código
independiente, los ejemplos de `demo-system/`, los fondos identificados en
`DEMO-ASSETS.md`, la licencia y el lanzador. No necesita compilar una imagen.

## Dentro de Fedora

Transfiere el archivo a la VM de Boxes y extráelo. Entra en `prosperus-demo-v2`,
la carpeta que contiene `iniciar.sh`, y abre una terminal allí:

```bash
sudo dnf install --setopt=install_weak_deps=False python3-pyside6 qt6-qtwayland python3-gobject
sh iniciar.sh
```

No hay que entrar en la subcarpeta `prosperus/`. El lanzador resuelve sus propias
rutas; también se puede ejecutar indicando la ruta completa de `iniciar.sh`.
Si las dependencias ya están presentes, basta con ejecutar el lanzador.

## Comprobar la experiencia

1. Abre Bienvenida y compara sus ocho tarjetas y su fondo con la demo de Obsidian.
2. Abre Carpetas. Recorre portadas con la rueda/flechas: el escritorio no cambia
   hasta pulsar la portada o Intro. Prueba el filtro, Fijar y el borde izquierdo.
3. Abre Laboratorio y entra en Apuntes: conserva el wallpaper y la paleta azul.
4. Abre dos notas. Mueve, redimensiona, minimiza y recupera; cambia de proyecto
   y vuelve para comprobar las ventanas de cada carpeta.
5. En una nota de ejemplo, pulsa Editar, escribe Markdown, guarda con Ctrl+S y
   vuelve a Vista previa. Cierra y abre la nota para comprobar el archivo.
6. Crea una carpeta y una nota. Abre Explorar y busca `hipotesis` sin acento.
7. Abre Aplicaciones, busca una herramienta instalada, fíjala y ábrela. El
   programa utiliza sus permisos normales dentro de Fedora; esto no prueba
   aislamiento de aplicaciones por proyecto.

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
