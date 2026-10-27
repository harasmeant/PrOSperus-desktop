# Probar el prototipo

## Requisitos

- Obsidian de escritorio. El manifiesto declara una versión mínima de `1.10.6`.
- El complemento comunitario Hover Editor, instalado por separado y activado, para las notas flotantes.
- Para el lanzador: Linux, Python 3 y PyGObject con GIO disponibles en el anfitrión.
- VSCodium instalado y su protocolo registrado si se quieren abrir archivos `.py` desde el mapa.

## Instalación manual

1. Crea una bóveda de prueba y copia dentro el contenido de `demo/`.
2. Dentro de esa bóveda, crea `.obsidian/plugins/project-desktop/`.
3. Copia desde `prototype/obsidian/` los archivos `manifest.json`, `main.js`, `styles.css` y `applications.py` a esa carpeta.
4. Reinicia Obsidian y activa **Escritorio de proyectos** en los complementos comunitarios.
5. Ejecuta **Escritorio de proyectos: Abrir escritorio del proyecto** desde la paleta.

No hay paso de compilación. El manifiesto del complemento conserva `0.1.0`; la versión del proyecto Linux se identifica por `VERSION` y la etiqueta Git `v0.0`.

## Aplicaciones Linux

En la barra inferior, abre **Aplicaciones** y pulsa **Actualizar lista**. El catálogo se genera en tu equipo; no se incluye el catálogo del autor. La detección y el lanzamiento usan GIO y las entradas de escritorio del sistema.

Si Obsidian está instalado mediante Flatpak, el lanzador usa `flatpak-spawn --host`. Requiere una autorización explícita del usuario:

```sh
flatpak override --user --talk-name=org.freedesktop.Flatpak md.obsidian.Obsidian
```

Reinicia Obsidian después. Este permiso amplía el acceso de Obsidian y sus complementos al anfitrión; no proporciona aislamiento por proyecto. La navegación y edición de notas no necesitan ese permiso. No se configura automáticamente al instalar el prototipo.

## Uso

Abre carpetas desde el mapa o el lateral. Las notas se abren en ventanas flotantes. Minimízalas para recuperarlas desde la barra durante la misma sesión. Usa **Explorar bóveda** para gestionar archivos mediante los diálogos y operaciones de Obsidian.

Para personalizar fondos, coloca una imagen llamada `wallpaper.png`, `wallpaper.jpg`, `wallpaper.jpeg`, `wallpaper.webp` o `wallpaper.avif` en una carpeta. Las subcarpetas heredan el fondo más cercano. Las paletas se definen en `PALETTES`, al comienzo de `main.js`.

## Desinstalar

Desactiva el complemento y elimina su carpeta si lo deseas. Las notas y los fondos permanecen en la bóveda. La autorización de Flatpak, si se concedió, se gestiona por separado.
