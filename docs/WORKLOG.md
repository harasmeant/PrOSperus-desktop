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

### Continuación remota autorizada · 2026-10-29

- A petición del usuario, detenida su VM Fedora de Boxes mediante managed-save de libvirt: estado inactivo y sesión guardada confirmados. Se conserva la RAM de la sesión Live en disco; no se ordenó apagar el sistema invitado ni se borraron sus datos.
- RAM disponible tras guardar la VM: 5,2 GiB.
- Arranque UEFI real de la ISO corregida confirmado: kernel, raíz Live y graphical.target en unos 7,5 s. La sesión gráfica falló por ausencia de pam_systemd.so; se incorpora systemd-pam y se repite la construcción.

#### Primera ISO funcional · v0.3.2-live.1

- Dependencia adicional de sesión: systemd-pam. Arranque desde CD UEFI con OVMF, dos CPU y 2048 MiB; sin red ni disco invitado.
- Interfaz verificada visualmente: proyecto prueba iso, nota validacion, texto impresora dentro de la nota guardado, cierre del editor y búsqueda por impresora mostrando validacion.
- Capturas en out/iso/screenshots y vista inicial en docs/images/iso-live-preview.png.
- ISO: 757.944.320 bytes; SHA-256 `ab729c0a2bb13a6e7b9121eedf0c6ab80eb8223d7566ee134a4f7377edbf2aa2`. Sustituye las imágenes de prueba anteriores.
- La VM Fedora del usuario permanece detenida con estado gestionado guardado por libvirt; no se descartó la sesión Live.
- No se afirma validación en hardware físico ni en Boxes. No incluye instalador ni persistencia.

## 30 de octubre de 2026 · Fibonacci y ultrawide · 0.4.0-dev

Usuario confirma espiral Fibonacci. Añadidos motor geométrico compartido, perfiles estándar/21:9/32:9, vista previa, anchura centrada y organización reversible de notas. Adaptador Sway experimental limitado al espacio visible del monitor seleccionado, excluyendo PrOSperus. Comentarios explican coordenadas lógicas, protección de otras pantallas y confirmación asíncrona de tamaños.

69 pruebas locales correctas. Sway aislado: cuatro aplicaciones, tres distribuciones, dos pantallas; geometrías verificadas y segunda pantalla sin cambios. La prueba detectó redondeo de tamaños de terminales: ahora se comprueba el resultado y se comunica el ajuste dentro de la zona. Cliente restringido probado. Evidencia en out/window-layouts.

Captura Qt real inspeccionada. El guion posterior espera el mapeado de la ventana antes de abrir el diálogo modal; su repetición quedó bloqueada por agotamiento de cuota de revisión automática de permisos, no por un rechazo de seguridad. La ISO publicada no se cambia. Integración completa de sesión y nueva ISO pendientes. Detalles: WINDOW-LAYOUTS.md.

Cierre: paquete local out/prosperus-demo-v4.tar.gz preparado, 7.648.493 bytes, SHA-256 ce947ca7e2fe548c8a08d2794981a71555abd051340ea7481b01331cbcd3f4a3. Extraído y comparado: 16 fuentes idénticas; arranque desde /tmp y captura correctos. No se ha publicado esta revisión ni reconstruido la ISO. Obsidian actualizado en notas 21, 22 e índice.

## 2 de noviembre de 2026 · Escritorio interactivo con Sway

- Sesión: Cage sustituido por Sway (`/etc/sway/prosperus.conf`). PrOSperus es la única ventana en mosaico (fondo); las aplicaciones flotan encima.
- `window_manager.py`: escucha eventos de Sway y coloca cada aplicación nueva en Fibonacci o pantalla completa (botón en la barra). Los diálogos no se tocan.
- Cada proyecto es un espacio de Sway; «General» es el escritorio con todos los proyectos y es el de inicio. Las aplicaciones arrancan en la carpeta del proyecto.
- Super+D oculta/restaura las aplicaciones del proyecto; Super+F, Super+Q, Super+Esc, Alt+Tab en Sway.
- Mapa: muestra todos los archivos (no solo .md); los que no son notas se abren con su aplicación. Carpetas compactas con su contenido en ramas (4 + «+N más»), animación de expansión al entrar.
- Tab / Mayús+Tab recorren las carpetas del mapa en sentido horario/antihorario. Super+Tab / Super+Mayús+Tab recorren el selector de proyectos; al soltar Super se abre.
- Apps de trabajo aparcadas en `image/Containerfile.apps` (sin construir). Restaurados ISO-LIVE.md y ARQUITECTURA-DISTRO.md, dañados por ediciones automáticas.
- Verificado: 77 pruebas; laboratorio Sway sin pantalla (contenedor window-tests, sin red, 768 MiB) con dos terminales: Fibonacci automático, cambio de proyecto, ocultar/restaurar y pantalla completa. Pendiente: reconstruir imagen/ISO y probar en la VM con ratón real.
- Arranque real de la imagen (QEMU/KVM, 2 GiB, snapshot): escritorio visible, dos terminales foot (Super+Intro) en Fibonacci sobre el mapa, red por NetworkManager (ping a fedoraproject.org), Python 3.14.8 y pip 26.0.1.
- Corregida carrera de arranque: el escritorio se movía a «General» antes de existir y quedaba oculto en el espacio «1». Ahora se espera a la ventana y se comprueba la respuesta de Sway. La salida de la sesión va al diario (`journalctl -t prosperus-session`).
- Añadidos foot, sudo (sin contraseña solo en la imagen de desarrollo), git, nano, curl, pip y NetworkManager habilitado. Guía: docs/TERMINAL-RED-PYTHON.md.
- Asistente de controladores (`driver_assistant.py`): detecta gráficas PCI y recomienda. Intel/AMD → pila libre (kernel-modules, linux-firmware, mesa-vulkan-drivers). NVIDIA Turing+ → propietario de RPM Fusion (akmod-nvidia + CUDA) o libre (nouveau + NVK); con Secure Boot añade el registro de clave MOK. NVIDIA anterior → nouveau. VM → nada. La instalación se abre en foot con las órdenes visibles. En la sesión del sistema se ofrece una vez por gráfica al arrancar; también en Controles › Hardware y drivers. Pruebas unitarias generadas con OpenRouter y corregidas. Sin probar en hardware NVIDIA real; sin persistencia, el controlador se pierde al apagar.
- VM a la resolución de la demo (1360×850): `virtio-vga,xres/yres` en run-vm.sh y `output Virtual-1 mode --custom 1360x850` en Sway (antes Sway elegía 640×480 y el escritorio quedaba recortado). Socket QMP añadido a run-vm.sh para capturas. Imagen reconstruida con el asistente de controladores; arranque y captura comprobados.
- Aplicaciones con barra de título propia (`border csd`): cerrar, maximizar y arrastrar desde la barra; Super+arrastrar también mueve. Sway no implementa minimizar: Super+M y el clic en la barra inferior sobre la aplicación enfocada la llevan al espacio de ocultas. Comprobado en la VM con dos foot.
- «Nueva nota» y «Nueva carpeta» piden nombre y destino; el destino propuesto es la carpeta actual. «Mover a otro proyecto…» en el menú contextual (`Vault.move`, sin sobrescribir; exige cerrar antes las notas abiertas). 90 pruebas correctas. Funciones de `Vault` generadas con OpenRouter y corregidas (la comprobación «dentro de sí misma» quedaba anulada por su propio `except`).
- Pendiente: una ventana recién abierta puede quedar algo más grande que su zona Fibonacci hasta la siguiente reorganización (aviso «Distribución incompleta»).

## 2 de noviembre de 2026 · Mapa radial, paneles y servicios del sistema

- Mapa: rejilla radial concéntrica (`concentric_slots`, `link_order` en `map_layout.py`) en lugar del reparto por fuerzas, que amontonaba tarjetas. Anillos a medio paso, sin solapes y dentro de la pantalla; las notas enlazadas quedan contiguas. Todas las líneas son curvas.
- Arrastrar tarjetas: encajan en el hueco más cercano o se intercambian (solo durante la sesión). Soltar una nota sobre una carpeta la mueve dentro; las carpetas solo cambian de hueco.
- Flechas: solo mueven la selección; Intro abre, Retroceso vuelve. Con el ratón encima, Intro abre esa tarjeta.
- Menos botones: «Crear» (esquina izquierda, se despliega al pasar el ratón: notas, carpetas, proyectos, importar, pegar, actualizar). Panel «Sistema» (esquina derecha: brillo, volumen, wifi, bluetooth, notificaciones, controles, ayuda). El dock solo muestra lo abierto y las favoritas.
- Super abre «Buscar» con tres modos: Archivos (proyectos), Programas y Todo (incluye `plocate` sobre el disco). Reiniciar y Apagar están ahí.
- Instalador de programas (`installer.py`): Fedora (dnf5, caché local) y Flathub; sigue instalando en segundo plano si se cierra la ventana. Selector de fondos por carpeta. Cabecera propia sin la barra de Qt.
- Imagen: kernel-modules, PipeWire, WirePlumber, BlueZ, brightnessctl, mako, plocate, NetworkManager-tui, flatpak con Flathub; índices de dnf/Flathub precargados. Notificaciones con mako y tono opcional. La VM tiene sonido (intel-hda → PipeWire del anfitrión), sigue en 2 GiB.
- Fondos y tono de notificación personales excluidos de git (derechos sin aclarar); solo se usan en la imagen local.
- 98 pruebas correctas.

## 2 de noviembre de 2026 · ISO para USB con persistencia y asistente Claude

- ISO híbrida (`-isohybrid-gpt-basdat`): grabada en un USB arranca un ordenador real por UEFI (Secure Boot desactivado; la imagen no está firmada).
- `scripts/write-usb.sh ISO /dev/sdX`: graba la ISO y añade la partición ext4 `PROSPERUS_DATA` con el espacio libre. Solo acepta USB/extraíbles sin particiones montadas y pide confirmar con `SI`.
- `prosperus-persistence.service`: al arrancar monta `/home/prosperus` y las redes Wi-Fi desde `PROSPERUS_DATA`. El primer arranque copia la carpeta personal de la imagen. Sin partición, la sesión sigue en RAM.
- Claude Code instalado para el usuario `prosperus` (instalador oficial). Super+C o «Asistente Claude» lo abren en `~/Proyectos`; con persistencia se conservan el inicio de sesión y las actualizaciones.
- Firmware Wi-Fi/gráficas (Intel, Realtek, Atheros, Broadcom, MediaTek, AMD) y controladores USB/NVMe en el initramfs para equipos reales.
- Comprobado: tabla GPT de la ISO, `write-usb.sh` sobre un archivo de 6 GiB (partición 4 ext4 `PROSPERUS_DATA`) y el contenido de la imagen. Aún sin probar en un equipo físico. No se ha usado OpenRouter: devolvía 429.

## 2 de noviembre de 2026 · Varios monitores

- `display_settings.py`: diálogo «Monitores» (Sistema → Controles) para extender (principal y lado), duplicar con `wl-mirror` o usar solo la principal. Se guarda en `~/.config/prosperus/displays.json` y Sway lo aplica al iniciar.
- Sway: Super+Mayús+flecha mueve la ventana a otro monitor; Super+Ctrl+flecha cambia el foco.
- Imagen: paquete `wl-mirror`. 107 pruebas correctas. OpenRouter devolvió 429; el código lo escribió Claude.
- Notas: siguen el botón «Fibonacci / Pantalla completa» del dock (antes solo afectaba a aplicaciones). En Fibonacci se reparten sin solaparse al abrir, cerrar o cambiar de modo; en Pantalla completa la nota ocupa todo el escritorio. Botón «□ Ampliar / ❐ Restaurar» en cada nota. 110 pruebas correctas.
- Controles de ventana discretos (`window_controls.py`): tres puntos (minimizar, ampliar, cerrar) que crecen con su símbolo al pasar el ratón. En notas y en las ventanas propias (instalador, fondos: ampliar y cerrar). Para aplicaciones externas, `prosperus-handle` dibuja una píldora flotante centrada sobre el borde superior de la ventana enfocada (Sway no tiene botones); actúa por con_id y no roba el foco. Pendiente de probar en la VM. 115 pruebas correctas.
