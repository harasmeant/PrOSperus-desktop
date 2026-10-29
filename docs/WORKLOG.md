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

## 29 de octubre de 2026 · Crear proyectos, copiar y usar el teclado

Nicolás confirma que la demo publicada abre y funciona en Fedora. Pide una
acción explícita para crear proyectos, copiar carpetas y notas cómodamente y
usar atajos habituales de escritorio, incluida Windows/Super y las funciones
del teclado. Esa confirmación corresponde a v0.2; v0.3 requiere una nueva prueba
en su VM.

### Implementado en 0.3.0-dev

- Nuevo proyecto en cabecera y tarjetero, siempre en la raíz; importar proyecto
  copia una carpeta externa sin cambiar el original.
- Selección simple, Ctrl+clic múltiple, doble clic/Intro para abrir; menú de
  clic derecho, copiar/pegar/duplicar y Ctrl+A en la página/lista actual.
- Portapapeles de archivos compatible con URI locales y formato de copia de
  GNOME. El editor conserva sus atajos de texto. La copia usa el archivo guardado.
- Importación desde diálogos y arrastre al mapa: sobre una carpeta se copia
  dentro; sobre el fondo, en la carpeta actual. Nunca solicita mover el origen.
- Copias en segundo plano; nombres alternativos ante colisiones; se retiran
  solo las salidas de la operación al fallar. Se rechazan enlaces simbólicos,
  archivos especiales y copiar una carpeta dentro de sí misma.
- F1, F5, F11, Ctrl+Espacio, Ctrl+Alt+N, Ctrl+Mayús+N, Ctrl+W y navegación con
  Alt+flechas. Cerrar una nota toma en cuenta cuál tiene el foco.
- Manejador de Super al soltar, sin abrir Aplicaciones tras una combinación;
  Super+E/D/I. Se desregistra al destruir la ventana para evitar accesos a Qt
  ya destruido. Los diálogos comparten el contexto correcto de portapapeles.
- Panel de controles con herramientas reales de la sesión: wpctl, playerctl y
  brightnessctl. Sin herramientas, o sin dispositivo para brillo, se desactiva
  el botón. Teclas multimedia atendidas solo en el modo de sesión propia.

### Comprobaciones y límites

- 45 pruebas locales: 27 anteriores y 18 sobre copias, conservación del origen,
  colisiones, permisos, recuperación tras fallo, selección, portapapeles,
  arrastre, creación de proyectos y teclado. Controles de audio/brillo simulados:
  no se modifica el anfitrión durante las pruebas.
- Capturas Qt a 1360×850 y 900×650, tarjetero, explorador y controles. Los títulos
  largos se abrevian en una línea y mantienen el nombre completo en la ayuda.
- Paquete `out/prosperus-demo-v3.tar.gz` preparado (7.64 MB), separado de v2.
  SHA-256: `844b67c91ae96525099b603eaba1c319354d0240ffc93fe21a3d87f2331fe8b2`.
  Extraído en una carpeta temporal: 12 fuentes Python y 15 archivos de ejemplo
  coinciden con el repositorio. `iniciar.sh` arranca desde `/tmp` y emite
  `PROSPERUS_READY 0.3.0-dev` sin errores. Renderizado del código empaquetado
  comprobado. Evidencia: `out/verification-v3.json`; siete capturas `fedora-v3-*`.
- La demo sigue siendo una ventana dentro de GNOME. Super, Alt+Tab y otras
  combinaciones reservadas dependen del compositor; F11 no cambia esa propiedad.
  Ctrl+Espacio es la alternativa para Aplicaciones. No se han cambiado ajustes
  globales del anfitrión o de la VM.
- No se ha reconstruido la imagen ni probado volumen, reproducción, brillo,
  portapapeles entre aplicaciones o teclas globales en Wayland/Boxes. La receta
  de sesión necesita completar integración global y audio antes de ofrecer
  una experiencia de escritorio completo.
- Copiar conserva enlaces tal como están; renombrar/mover/eliminar con
  actualización de enlaces y persistencia de ventanas siguen pendientes.
- v3 queda preparada localmente; la publicación GitHub existente sigue siendo
  v0.2.0-dev. No se ha reemplazado ni sobrescrito su descarga.

## 29 de octubre de 2026 · Buscar dentro de Markdown y desbloquear Fedora Live

Nicolás solicita buscar también dentro de los `.md`. Precisa con una captura
que el buscador de **Tus proyectos** debe devolver el escritorio **Cursos 3D**
al escribir **impresora** si esa palabra aparece en una de sus notas, aunque
no esté en el nombre del proyecto.

### Búsqueda entregada en 0.3.1-dev

- Mapa y explorador buscan en nombre/ruta y contenido guardado de notas,
  recursivamente. El tarjetero devuelve la portada del proyecto que contiene
  una nota coincidente; abrirla lleva al escritorio de ese proyecto.
- Búsqueda sin distinción de tildes/mayúsculas; todos los términos deben estar
  en la ruta o texto de la misma nota. Coincidencias de nombre primero.
- Se conservan los límites de lectura (2 MiB), rutas y carpetas ocultas. Los
  Markdown ilegibles o grandes aún pueden coincidir por nombre; no bloquean
  los demás resultados. No se indexan PDF ni texto sin guardar.
- Se lee una nota cada vez, sin mantener una copia de la bóveda en memoria.
  Es una búsqueda directa, sin índice persistente; el rendimiento con bóvedas
  grandes deberá medirse antes de incorporar indexación.

### Incidencia real de instalación

La transacción de DNF fallaba: `LiveOS_rootfs` tenía 777 MiB de capacidad,
183 MiB disponibles y 279 MB de caché. RPM pedía unos 387 MB adicionales;
quitar solo esa caché no bastaba. `/tmp` tenía 1.9 GiB libres. No se aumentó
la RAM ni se modificó el disco de la VM.

Se preparó un entorno Python en `/tmp/prosperus-runtime` con acceso a los
paquetes del sistema y se instaló únicamente `PySide6-Essentials` desde PyPI,
sin caché. Nicolás confirmó que v0.3 cargó y pudo importar una carpeta usando
ese entorno. Esto confirma arranque e importación; no prueba todas las funciones.

v3.1 añade `iniciar-live.sh` para reutilizarlo. El lanzador habitual admite
`PROSPERUS_PYTHON` y argumentos como `--root` para abrir la carpeta ya importada
de v3. El diagnóstico de dependencias muestra el error real y el espacio en
`/`, en vez de invitar a repetir una instalación que no cabe. El entorno de
`/tmp` desaparece al reiniciar; las notas deben conservarse fuera del Live.

### Verificación y entregable

- 51 pruebas pasan con el Qt del sistema y con PySide6 Essentials 6.12.0 en
  un entorno temporal (aproximadamente 258 MiB instalado).
- El caso específico **impresora → Cursos 3D** está probado en los tres
  buscadores con una nota ficticia en dos niveles de subcarpetas. Abrir la
  portada devuelve el escritorio del proyecto, no la carpeta de la nota.
- Paquete extraído y comparado con las fuentes. Arranque desde `/tmp` con el
  entorno ligero, `--root` externo al paquete y captura: correcto. Búsqueda
  por contenido con el código empaquetado: correcta; nota de prueba intacta.
- Paquete: `out/prosperus-demo-v3.1.tar.gz` (7.64 MB).
- SHA-256: `0071b07ce4008ef767d7673a76f42baafbf3cbae9d8a0db06603563ebfa3fee7`.
- Evidencia: `out/verification-v3.1.json` y capturas `fedora-v31-*`.
- La v3.1 queda local, sin publicar en GitHub. La comprobación manual en Fedora
  corresponde todavía a v0.3 con Essentials, no a este paquete nuevo.

### Consulta sobre la ISO

Se revisaron las recetas existentes: preparan un disco GPT/EFI con raíz ext4
y salida qcow2, no una ISO Live ni un instalador. Falta preparar y comprobar
el medio de arranque ISO/UEFI, integrar la sesión y dependencias, y validar
almacenamiento y recursos. Una ISO instalable requiere además instalación y
persistencia. No se inició una construcción de ISO ni se comprometió una fecha.

## 29 de octubre de 2026 · Corregir `iniciar.sh` en la sesión Live

Nicolás ejecutó el lanzador habitual de v3.1 y volvió a recibir
`ModuleNotFoundError: PySide6`: seleccionaba el Python de Fedora aunque el
entorno temporal ya estaba preparado. Era una falta de integración del
lanzador; no requería repetir la instalación.

- v3.2 usa un único lanzador: prueba Qt en el Python del sistema y, si falta,
  detecta `/tmp/prosperus-runtime`. Solo lo reutiliza cuando pertenece al usuario
  y su Python puede importar Qt. Respeta `PROSPERUS_PYTHON` y `--root`.
- El script fuente vive en `desktop/iniciar.sh` y se copia al paquete sin
  mantener otra implementación. Se ofrece suelto en `out/iniciar.sh` para
  sustituir el de v3.1 sin tocar los proyectos.
- La guía empieza por `sh iniciar.sh`, sin pedir instalar los RPM antes de
  comprobar si existe un entorno funcional. El diagnóstico del Live explica
  cómo reconstruir el entorno temporal si se ha reiniciado.
- 55 pruebas pasan. Cuatro comprueban elección del intérprete, entorno ligero,
  entorno roto, selección explícita y argumentos con espacios.
- Reproducción adicional real con Python `-S` sin PySide6: el lanzador selecciona
  Essentials y arranca. También se verificó la reparación de una línea mediante
  `sed` sobre el `iniciar.sh` exacto del paquete v3.1 y su posterior arranque.
- Paquete: `out/prosperus-demo-v3.2.tar.gz`.
- SHA-256: `ea8ab3ca35e8e76f70884767dde943596d4f09f9a1bf71f337a95b00f46ca95f`.
- Evidencia: `out/verification-v3.2.json`. Pendiente de confirmación en la VM
  del usuario; no se ha publicado esta revisión en GitHub.

## 29 de octubre de 2026 · Búsqueda confirmada en la VM

Nicolás confirma «ya busca bien» después de reparar el lanzador de la copia
v3.1 y arrancar con `sh iniciar.sh`. Queda validada por el usuario la búsqueda
solicitada sobre su carpeta importada, además del arranque con el entorno ligero.
Esta confirmación no verifica por sí sola la detección automática del paquete
v3.2, que se comprobó localmente.

La ruta sugerida `../prosperus-demo-v3/proyectos` no existía en su VM. Se
rectificó la indicación: usar la carpeta `proyectos/` de la copia actual, sin
suponer que se conserva una versión anterior. Al dar instrucciones futuras,
no añadir `--root` con una ruta no confirmada.

Se revisa la base del siguiente hito: existen recetas para disco GPT/EFI y
qcow2, pero ninguna receta ISO. La elección entre ISO de prueba y nuevas
funciones del escritorio se consulta antes de iniciar una construcción pesada.

### Publicación de las demos · 2026-10-29

- Preparada publicación v0.3.2-dev con código actual y paquetes históricos v3 y v3.1. Los históricos conservan sus limitaciones; se recomienda v3.2.
- 55 pruebas correctas antes de publicar; contenido Python y lanzador del paquete comparados con el código fuente.
- Corregido LEEME para no asumir que existe una carpeta anterior de proyectos.
- Paquete v3.2 regenerado: SHA-256 `1cad6a1f9869fcf423f72114382afff3211dc84fb335363b618f4db5df031b60`. Sustituye el hash anterior tras el ajuste de documentación.
- La ISO Live con dependencias incluidas sigue pendiente de construcción y prueba.

### ISO Live y legibilidad · 2026-10-29

- Añadidas recetas separadas de ISO: SquashFS con overlay temporal, dracut-live, UKI UEFI y El Torito/GPT; sin instalador ni persistencia.
- Construcción con límites de CPU/memoria; herramientas fuera de la imagen del usuario.
- La sesión copia los ejemplos al directorio del usuario para poder crear y guardar notas sin permisos de administrador.
- Comentarios añadidos a búsquedas, copias, trabajadores Qt, teclado Super, tarjetero, sesión y lanzadores.
- 55 pruebas locales correctas tras los primeros cambios; arranque de ISO pendiente de verificación.
- Se pidió cerrar la VM Fedora después de guardar las notas por presión de memoria del anfitrión (2,3 GiB disponibles y swap casi llena).
- CI de la publicación 0.3.2: las dos ejecuciones de GitHub Actions finalizaron correctamente.

#### Resultado de construcción y siguiente comprobación

- ISO corregida: 757.366.784 bytes (722,28 MiB), SHA-256 `b4d9dd8ade84fa810a8236fbb52626c6ed1d245d259249e8dd86599f84a10e0e`.
- Los 13 archivos Python de la ISO coinciden con el código actual, incluidos los comentarios. Qt/GIO y creación de proyecto/nota con búsqueda comprobados como usuario 1000 en el contenedor del sistema.
- Añadido módulo qemu-device-display-virtio-vga a las herramientas tras detectar su ausencia.
- OVMF no encontró el cargador con el FAT anexado fuera del volumen ISO. Se movió el FAT dentro del volumen (EFI/efiboot.img) y se regeneró el catálogo El Torito/GPT conservando el mismo SquashFS.
- La repetición del arranque fue detenida por la comprobación de RAM: 1,9 GiB disponibles y swap casi llena. No quedó ninguna VM de prueba activa.
- Pendiente: arrancar la ISO corregida, capturar la interfaz, crear/guardar/buscar una nota desde la VM y apagar. No se ha publicado la ISO como funcional.
- Comando de prueba reducida cuando haya margen: `PROSPERUS_VM_MEMORY_MB=1024 bash scripts/run-iso.sh`; la prueba normal usa 2048 MiB.
