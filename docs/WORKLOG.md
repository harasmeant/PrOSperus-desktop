# Diario de desarrollo · PrOSperus independiente

## 28 de octubre de 2026 · Referencia confirmada por Nicolás

Nicolás probó el prototipo 0.1 en Fedora Live dentro de GNOME Boxes. Navegación,
notas, minimización y búsqueda funcionan con fluidez, pero la experiencia está
muy lejos de la demo de Obsidian que compartió con sus colegas. Su preferencia
explícita es conservar esa apariencia y avanzar hacia su comportamiento.

**Referencia de producto:** el prototipo aceptado de Obsidian. No sustituirlo por
un diseño genérico de panel lateral fijo. Las capturas del cierre del 27/10 son
la referencia visual local: tarjetero vertical, mapa sobre wallpaper, paletas
por proyecto, notas flotantes y barra contextual inferior.

Nicolás cierra la VM para liberar recursos y autoriza seguir trabajando,
comprobando los cambios y documentando avances. La validación automática se
hace fuera de la VM y no debe presentarse como una prueba manual en Fedora.

### Trabajo de esta iteración

- Fondos originales de la demo reutilizados en proyectos con notas ficticias.
  No copiar bóvedas, preferencias privadas, catálogos personales ni capturas
  de Obsidian a los paquetes de prueba.
- Wallpaper heredado por las subcarpetas y por sus notas; paleta propia por
  proyecto y fondo neutro cuando una carpeta no proporciona imagen.
- Tarjetero vertical superpuesto, rueda/flechas, filtro, fijación y apertura
  desde el borde. Explorar portadas no cambia de proyecto hasta abrir una.
- Mapa radial con tarjetas, iconos y conexiones curvas; paginación.
- Barra desplazable con accesos de carpeta y notas abiertas/minimizadas.
- Notas flotantes con lectura y edición Markdown; guardado explícito,
  advertencia de cambios sin guardar y comprobación de modificaciones externas.
- Creación de notas/carpetas y explorador de proyectos.
- Buscador de aplicaciones Linux mediante el ayudante GIO ya usado por el
  prototipo; invocación asíncrona, sin construir órdenes de shell a partir de
  nombres. Favoritos globales guardados en la configuración de PrOSperus.

### Pendientes que deben seguir visibles

- Paridad completa con el gestor de Obsidian: renombrar, mover y eliminar con
  actualización de enlaces y recuperación todavía requieren diseño y pruebas.
- Edición Markdown con vista previa no equivale al editor visual de Obsidian.
- No hay aislamiento de aplicaciones por proyecto, ni integración de ventanas
  externas como nodos del mapa.
- La disposición de notas no se recupera tras cerrar la aplicación.
- La imagen qcow2 existente no se reconstruye en esta iteración; el entregable
  será un paquete actualizado para la VM Fedora ya preparada.

### Comprobaciones finalizadas

- 27 pruebas locales pasan: límites de rutas, creación, guardado y conflictos,
  permisos de archivo, lectura y enlaces, cambios sin guardar, geometría de
  notas, minimización, proyectos, teclado del tarjetero, filtro, herencia de
  fondos, barra desplazable y favoritos de aplicaciones.
- Las pruebas del límite GIO simulan el lanzamiento: ID exacto, aplicaciones
  ocultas/desconocidas, errores y aislamiento de la salida del programa.
- Catálogo GIO real consultado correctamente: 110 aplicaciones detectadas en
  el anfitrión. No se abrieron aplicaciones reales durante la verificación.
- Capturas Qt sin pantalla revisadas a 1360×850 y 900×650. Se corrigieron el
  recorte inferior de las notas, el contraste de enlaces y el estrechamiento
  de los accesos de la barra. La VM permaneció apagada.
- Paquete extraído en una carpeta temporal: sus fuentes coinciden con el
  repositorio y `iniciar.sh` arranca correctamente ejecutándolo desde `/tmp`,
  fuera de la carpeta del paquete. Captura adicional del código empaquetado.
- Sintaxis Python y comprobación de espacios en el diff correctas.

### Entrega preparada

- Versión de desarrollo: `0.2.0-dev`.
- Paquete: `out/prosperus-demo-v2.tar.gz` (7.63 MB decimales).
- SHA-256: `23f4d3eea0ce7d8a26bf4158f5be5a0d0c7fe36e73711ad63c16cf29172737a8`.
- Verificación resumida: `out/verification-v2.json`.
- Capturas: `out/screenshots/fedora-v2-map.png`, `fedora-v2-projects.png`,
  `fedora-v2-note.png`, `fedora-v2-small.png`, `fedora-v2-laboratory.png` y
  `fedora-v2-packaged.png`.
- Receta del paquete: `scripts/package-fedora-demo.py`.
- Guía para reanudar en Fedora: `docs/FEDORA-DEMO.md`.

**Validación pendiente:** la nueva versión todavía no se ha ejecutado
manualmente en la VM Fedora. Las pruebas locales y capturas no verifican
Wayland/Boxes ni el lanzamiento gráfico real dentro de esa máquina.

Al terminar esta iteración, la demo anterior se conservó por separado y no se
había hecho commit, push, publicación ni reconstrucción de la imagen qcow2.

## Publicación de esta versión · 28 de octubre de 2026

Nicolás pide crear el repositorio y subir la versión. El proyecto ya tiene el
remoto público `https://github.com/harasmeant/PrOSperus-desktop`, por lo que se
usa ese repositorio manteniendo su historial y su configuración.

Se prepara la publicación `v0.2.0-dev` como versión previa con el paquete de
Fedora y su SHA-256. La automatización conserva las pruebas de Obsidian y añade
las del escritorio independiente sobre Fedora 44, junto con el empaquetado y
una captura sin pantalla. La imagen experimental queda documentada aparte.
