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
- Controles de ventana discretos (`window_controls.py`): tres puntos (minimizar, ampliar, cerrar) que crecen con su símbolo al pasar el ratón. En notas y en las ventanas propias (instalador, fondos: ampliar y cerrar). Para aplicaciones externas, `prosperus-handle` dibuja una píldora flotante centrada sobre el borde superior de la ventana enfocada (Sway no tiene botones); actúa por con_id y no roba el foco. Comprobado en la VM con la ISO: la píldora sigue a la terminal (foot). 115 pruebas correctas.

## 2 de noviembre de 2026 · USB en equipo real: persistencia y pantalla negra

- Primera prueba en hardware (HP Pavilion, AMD Cezanne + NVIDIA GTX 1650): arrancaba pero quedaba en negro y `PROSPERUS_DATA` seguía vacía.
- Persistencia: el initramfs monta el disco USB entero (iso9660) y el kernel no deja abrir la partición 4 («is in use»). `prosperus-persistence` la abre ahora con un loop con desplazamiento. Comprobado arrancando la ISO como disco USB en QEMU (`usb-storage`): carpeta personal y registro guardados, ext4 limpio tras apagado ACPI.
- Pantalla negra: Sway podía arrancar sobre simpledrm antes de amdgpu. `prosperus-session` espera hasta 15 s a una gráfica real y fija `WLR_DRM_DEVICES` a la de arranque. Pendiente de confirmar en el portátil.
- El registro del sistema se guarda en `PROSPERUS_DATA/journal` (journald persistente solo con la partición). OpenRouter devolvió 429; el código lo escribió Claude.

## 2 de noviembre de 2026 · Sin teclado ni ratón en el portátil

- Segunda prueba: la persistencia funciona (registro guardado en `PROSPERUS_DATA/journal`), pero teclado y ratón no respondían.
- El registro termina a los 20 s, justo al abrir la sesión: journald solo escribía en disco cada 5 min y el apagado fue forzado, así que se perdió lo de Sway. El kernel sí detecta teclado interno, touchpad ELAN y los periféricos USB; amdgpu y nouveau cargan (nouveau sin firmware).
- `SyncIntervalSec=5s` en el registro del USB y volcado de `swaymsg -t get_inputs/get_outputs` al registro (`prosperus-diag`) para el siguiente intento.
- El escritorio se ve pero no responde a nada: lo más probable es que Sway se cuelgue con la NVIDIA (nouveau sin firmware). La ISO arranca ahora con `modprobe.blacklist=nouveau`; la pantalla interna va por la AMD. Pendiente de confirmar en el portátil.
- Confirmado en el portátil: con nouveau bloqueado el escritorio responde; teclado, ratón y el instalador de controladores funcionan.

## 2 de noviembre de 2026 · Escritorios en cuadrícula y controles de ventana

- «Tus proyectos» muestra los escritorios en cuadrícula (antes, tarjetero apilado): tarjetas con su fondo, nombre, notas y carpetas, marca «En uso» y realce al pasar el ratón. Flechas en las cuatro direcciones, Intro o clic abre; Super+Tab sigue recorriéndolos. El panel se ensancha a 660 px y las columnas se ajustan al ancho.
- Controles de ventana: en reposo, puntos grises discretos que toman su color al desplegarse; anillo sobre el botón señalado; estado pulsado; el clic solo actúa si se suelta sobre el mismo botón; «Ampliar» pasa a «Restaurar» (icono de dos ventanas) en notas, ventanas propias y la píldora de aplicaciones; descripción emergente por botón. La píldora lleva un borde fino y olvida la geometría guardada de las ventanas que cierra.
- OpenRouter devolvió 429; el código lo escribió Claude. 117 pruebas correctas.
- La píldora de las aplicaciones se coloca encima de la ventana (antes tapaba sus primeras líneas) y solo entra dentro si la ventana está pegada arriba. Sway imponía 75×50 a las flotantes: `floating_minimum_size 24 x 24` deja la píldora en 100×32. Comprobado en Sway sin pantalla (contenedor window-tests) con foot. 117 pruebas correctas.

## 2 de noviembre de 2026 · Estética: fondo y radios del mapa

- Fondo del escritorio: el velo negro uniforme pasa a ser un degradado teñido con el tono de la carpeta (como `--pd-shade` del prototipo). Oscurece arriba (títulos) y abajo (dock) y deja ver la foto en el centro.
- Mapa: las tarjetas van en radios equiespaciados alrededor de la carpeta (3, 4, … hasta 8 por página; la siguiente página sigue el mismo patrón), como en el prototipo de Obsidian. Los enlaces entre notas solo deciden el orden: las más enlazadas quedan en radios vecinos. OpenRouter devolvió 429; el código lo escribió Claude.
- Ramas de árbol en el mapa (`branches.py`): los radios son troncos que se afinan desde la carpeta, las notas hijas salen como ramitas y cada rama lleva hojas alternas; los enlaces entre notas son ramas finas curvadas hacia fuera. Base para estilos de rama según el fondo (técnico, fantasía…).
- Ramas en estilo enredadera monocroma (inspirada en la incrustación «árbol de la vida» de las guitarras): curva en S que se afina, brotes alternos que acaban en hoja con nervio o en zarcillo en espiral, hojita al otro lado y brote final junto al nodo. Un solo color (tono nácar del texto) variando la opacidad. Las ramas ya no se ven a través de las tarjetas.
- Ramas procedurales: el estilo sale del fondo de la carpeta (`wallpaper_traits`), sin elegirlo a mano; las carpetas nuevas heredan fondo y ramas, y solo se recalcula si cambia el archivo del fondo. Rasgos: rectitud (bordes rectos y largos → de enredadera a brazo articulado con codos, articulaciones, tornillos y pistones), detalle (más o menos brotes) y brillo (setas y destellos). Los codos giran todos hacia el mismo lado para que los brazos vecinos no se crucen. Comparación en `docs/images/ramas-procedurales.png`. 118 pruebas correctas.
- Estilo técnico cambiado a filigrana art déco (a petición): arco de compás en doble línea, grecas (espirales cuadradas), rombos con nervio y puntos de compás. «Magia» se mide ahora por el tono ámbar del fondo (los de DND dan 0,4-0,6; el resto ≤0,08) y añade setas y destellos.
- Fantasía en art nouveau: tronco en latigazo (todos con el mismo giro para no cruzarse), tallos largos y sinuosos con perlas que acaban en lirio, ojo de pluma de pavo real, zarcillo o seta (siempre hacia arriba), más brotes y destellos sutiles. Tres estilos artísticos según el fondo: árbol de la vida (natural), art déco (rectitud) y art nouveau (ámbar/fantasía). Comparación actualizada en `docs/images/ramas-procedurales.png`.
- Aplicación «Ramas» (`prosperus-ramas`, `branch_settings.py`): personaliza las ramas de la carpeta actual con vista previa en directo sobre su fondo. Automático (según el fondo) o estilo a mano (art déco, art nouveau, brotes); retoques de curvatura, grosor y opacidad. Adornos: piezas de serie (seta, lirio, ojo de pavo real, zarcillo, hoja, greca, rombo, destello) o imágenes propias, cada uno con «1 de cada N brotes», sitio (sobre la rama o al final de un tallo), tamaño y tinte. Las imágenes se copian a `.prosperus-adornos/` y los ajustes a `.prosperus-ramas.json`; las subcarpetas lo heredan y el escritorio se actualiza al guardar. Solo se aceptan imágenes dentro de esa carpeta (sin rutas). 121 pruebas correctas. OpenRouter no se usó (429 toda la sesión).
- Adornos por barra en vez de «1 de cada N brotes»: frecuencia 0-1 (0 nunca, 1 cada 6 px a lo largo de la rama), ángulo 0-180° respecto a la rama con lado horario, antihorario o ambos alternando, superposición (la de fuera o la de dentro encima), sitio, tamaño, opacidad y tinte. Gradiente opcional de tamaño, ángulo y opacidad del principio al final de la rama (alas de plumas). Pieza nueva: pluma. Las imágenes propias giran con el ángulo. Los ajustes antiguos se convierten solos. 121 pruebas correctas.
- Gradiente propio de la rama, independiente del de los adornos: opacidad al final y luz al principio/al final (más clara u oscura sin salir del tono de la carpeta). Los brotes toman el color de su tramo; los adornos conservan su gradiente.
- Formatos de pantalla: probado el escritorio a 1920×1080 (16:9), 1280×800 (16:10), 2560×1080 y 3440×1440 (21:9) y 1024×768 (4:3). En 21:9 la elipse se estiraba hasta los bordes: ahora no pasa de 2,3 veces su alto (`map_metrics`, compartido con la vista previa). En pantallas estrechas las hojas que no caben hacia fuera van debajo o encima de su tarjeta (antes tapaban la tarjeta). La vista previa de «Ramas» dibuja el escritorio entero a escala con la proporción de la pantalla y permite verlo en 16:9, 16:10, 21:9, 32:9 y 4:3 (`docs/images/ramas-formatos.png`). 122 pruebas correctas.
- Con un número impar de carpetas (3, 5, 7) los radios no llegaban abajo y la figura quedaba aplastada y descentrada (con 3, dos tarjetas casi a la altura del centro). `radial_slots` encaja ahora la figura en el óvalo (centrada y tocando los bordes) sin cambiar orden ni simetría. La vista previa de «Ramas» usa tantas tarjetas como subcarpetas (3-8). Capturas con 3 carpetas en 16:9, 21:9 y 4:3: `docs/images/tres-carpetas.png`.
- «Ramas»: los controles van en una zona con desplazamiento y la ventana se ajusta al alto disponible (cabe en 850 px con los dos gradientes abiertos). Etiquetas de hojas con 120 px mínimo: en 4:3 ya no se recortan. Detección de fondos técnicos por círculos o líneas finas (engranajes, planos): probada y descartada, no distingue un engranaje de unas ondas; para esos fondos, modo a mano en «Ramas».
- Ventanas más suaves: paleta con menos contraste (fondos algo más claros, bordes y acento apagados, texto perla en vez de blanco), botones más cómodos (esquinas de 12 px, 10×18 px de relleno, estados de pasar por encima, pulsado y foco), menús redondeados y espaciosos, campos, listas, casillas y consejos con el mismo estilo. El anillo de foco ya no enmarca las notas (solo en alto contraste).
- Brillo y volumen: las barras solo aplicaban al soltar el arrastre (clic en la barra, rueda o flechas no hacían nada). Ahora aplican con cualquier cambio (120 ms de espera), no reenvían lo que acaban de leer del sistema y muestran un aviso si la orden falla (el motivo queda en el journal como `prosperus-panel`). Teclas del portátil en Sway (volumen, silencio, micro, brillo; también bloqueado). Usuario en los grupos `video` y `audio` para que brightnessctl funcione aunque logind no lo permita. Al entrar se guarda `brightnessctl -l` y `wpctl status` en el journal (`journalctl -t prosperus-diag`) para diagnosticar el portátil. 123 pruebas correctas.
- Tema floral en las ventanas: remate de enredadera (`flourish` en `branches.py`) bajo el título de las notas, de las ventanas propias (Ramas, Fondos, Instalador) y sobre el pie del panel Sistema; centrado, con 560 px como máximo, y en el estilo procedural del fondo de la nota (déco, nouveau o árbol de la vida). No aparece en alto contraste. Panel Sistema más abierto: títulos de sección, barras de brillo y volumen a todo el ancho con su porcentaje, botones más grandes (esquinas de 12 px), más márgenes. «Ramas» con secciones «Estilo de la rama» y «Adornos», filas separadas y el menú de añadir indicado con ▾. Capturas: `docs/images/ventana-ramas-floral.png`, `docs/images/panel-sistema.png` (fondo de demostración). 123 pruebas correctas.
- Ventana de Aplicaciones, probada dentro de la imagen en un Sway sin pantalla:
  - Sway la pegaba al lado del escritorio y partía la pantalla en dos. Lo mismo pasaba con Explorar, Atajos y Acerca de, porque comparten `app_id` con el escritorio y la regla `floating disable` las alcanzaba. La regla ahora solo afecta a la ventana titulada «PrOSperus desktop»; los diálogos flotan centrados.
  - Qt no tenía tema de iconos en Sway: ahora usa Adwaita, con AdwaitaLegacy de respaldo.
  - Los nombres se cortaban y no salían bajo los iconos propios: celdas de 120×104 a dos líneas.
  - Buscador a tamaño cómodo.
  - Los programas de Flathub no aparecían porque greetd no lee `/etc/profile.d`; la sesión ya exporta sus rutas en `XDG_DATA_DIRS`.
  - Comprobado: el catálogo muestra los 7 programas y «Abrir» lanza Foot, que el gestor coloca flotando.
  - `app_item` y su prueba los escribió qwen2.5-coder:7b en local (Ollama), con una ronda de correcciones. 125 pruebas correctas.
- Notas translúcidas: fondo del color del panel al 60 % (40 % de transparencia), sin la copia del fondo de pantalla, para que se vea el escritorio de detrás. En alto contraste siguen opacas.
- Consola Foot translúcida: el fondo entero, incluida la barra de título, al 60 %, con una paleta suave a juego (colores propuestos por qwen2.5-coder; el gris claro se corrigió porque no se leía). Se valoró Konsole a petición, pero se descartó porque arrastra unos 120 paquetes de KDE.
- Renombrar y mover a la papelera:
  - Menú contextual «Renombrar…» (F2) y «Mover a la papelera» (Supr) para notas y carpetas.
  - Al renombrar una nota se actualizan sus wikilinks en todas las notas (`[[Plan]]`, `[[Plan|texto]]`, `[[carpeta/Plan#título]]`, `[[Plan.md]]`), sin tocar los bloques de código.
  - La papelera es `.papelera` en la raíz de los proyectos: oculta, nada se borra y nunca se sobrescribe (`Nota (2).md`).
  - Con una nota abierta se pide cerrarla antes.
  - `rename_wikilinks` la escribió qwen2.5-coder en local, con un esqueleto guiado y dos correcciones (barra del prefijo y el sufijo `.md`, que era un error de la especificación). 127 pruebas correctas.
- Animaciones suaves (`motion.py`, borrador de qwen2.5-coder revisado: animaciones que se pisan con clics rápidos y widgets borrados a mitad):
  - El panel de proyectos entra deslizándose desde la izquierda (260 ms) con las tarjetas apareciendo escalonadas, y sale deslizándose (una imagen del panel, que queda oculto al momento).
  - El resaltado de las tarjetas al pasar el ratón se funde (160 ms).
  - En el mapa, las hojas aparecen con fundido al entrar o salir de una carpeta, en vez de saltar.
  - Al cambiar de página, las tarjetas entran desde el lado hacia el que se avanza, con fundido.
  - Fotogramas en `docs/images/animaciones-fotogramas.png`.
- Corregido un fallo de esta noche: el `min-height` general de los botones aplastaba las tarjetas del panel de proyectos a 42 px. Se quitó y las tarjetas recuperan su alto aunque una hoja de estilo (botones grandes) lo cambie. 127 pruebas correctas.
- Cerrar, minimizar y maximizar, probados en un Sway sin pantalla con la píldora, Foot y Ramas:
  - Al abrir una aplicación, el gestor intentaba colocarla antes de su primer dibujo. Sway le imponía su tamaño flotante por defecto (media pantalla) y salía «No se pudo organizar: distribución incompleta» cada vez. Ahora reintenta hasta cuatro veces, cada 250 ms, y la ventana se abre ya colocada.
  - Foot mostraba sus propios botones de minimizar y maximizar, que Sway ignora (no hacían nada). Se han quitado (`button-width=0`, sin doble clic para maximizar) y la píldora queda como único control: en las pruebas, ampliar, restaurar, minimizar, recuperar desde la barra y cerrar funcionan.
  - En Sway, «Ampliar» de las ventanas propias (Ramas, Fondos, Instalador) no hacía nada (`showMaximized` se ignora). Ahora amplía por IPC como la píldora (900×700 → 1600×900 → 900×700 comprobado).
  - La prueba unitaria de esto la escribió qwen2.5-coder. 128 pruebas correctas.
- Recuperar desde la papelera: «Crear › Papelera» muestra lo borrado y la carpeta de la que salió (`.papelera/.origen.json`). «Recuperar» o doble clic lo devuelve a su sitio sin sobrescribir (`Nota (2).md`); si esa carpeta ya no existe, va a la raíz. Icono nuevo de papelera. Captura: `docs/images/papelera.png`.
- Al renombrar también se actualizan los enlaces Markdown relativos (`[texto](../A/Plan.md#título)`), en notas y carpetas: los enlaces a notas que hay dentro de una carpeta renombrada pasan a la nueva ruta. Se respetan los enlaces externos, los títulos de enlace y los bloques de código. Borrador de qwen2.5-coder: lo aplicaba dentro del código y no contemplaba carpetas; corregido.
- Al cambiar de página o abrir una carpeta, cada rama se funde con su tarjeta en vez de dibujarse antes de que llegue. 130 pruebas correctas.
- Dos pantallas:
  - La pantalla sin el mapa mostraba un color liso; ahora muestra el fondo del proyecto actual (`output * bg … fill`, solo cuando cambia). Probado en Sway con dos salidas virtuales.
  - En el portátil (HP con AMD + GTX 1650), la pantalla externa por HDMI probablemente cuelga de la NVIDIA. Con nouveau bloqueado (colgaba Sway), esa salida no existe hasta instalar el controlador propietario. Para saber qué pasa: `journalctl -t prosperus-diag` muestra las salidas que ve Sway. 131 pruebas correctas.
- Persistencia: con la partición `PROSPERUS_DATA`, los programas de Flathub (`/var/lib/flatpak`) se guardan en el USB y se conservan entre arranques. El primer arranque copia el catálogo de la imagen. Los de Fedora siguen perdiéndose: el sistema base no se escribe. El instalador avisa de qué se conserva según haya persistencia o no. 132 pruebas correctas.

## 3 de noviembre de 2026 · Vuelve el tarjetero de proyectos

- «Tus proyectos» recupera el tarjetero apilado (portadas en vertical, rueda o ↑ ↓, clic en la portada para abrir) en lugar de la cuadrícula, a petición. Se conservan las animaciones del panel (entrada y salida por la izquierda, portadas que aparecen una tras otra). El panel vuelve a 370 px. 132 pruebas correctas.
- Después, a petición: la cuadrícula queda como opción. Botón con icono junto a «Fijar» que alterna tarjetero ↔ cuadrícula; se guarda en `projects/view` (por defecto, tarjetero). El panel mide 370 px con el tarjetero y 660 px con la cuadrícula. 133 pruebas correctas.
- Código en las notas: los bloques ` ```python `, ` ```java ` (y unos 500 lenguajes más) se ven con fondo propio, letra monoespaciada y colores suaves a juego con la consola: palabras clave, cadenas, comentarios en cursiva, números, funciones, clases y decoradores. Los colores los da Pygments (`python3-pygments` añadido a la imagen base). Sin él, o con un lenguaje desconocido, el bloque conserva el fondo y la letra. `highlight_spans` la escribió qwen2.5-coder, correcta a la primera. Captura: `docs/images/nota-codigo.png`. 134 pruebas correctas.
- Gráficas en las notas: un bloque ` ```grafica ` con una tabla (primera fila: nombre de las series; separador `,` o `;`, con `;` se admite la coma decimal) se dibuja como imagen. Admite `tipo: barras | lineas | tarta` y `titulo:`, hasta 6 series y 60 filas, con escala redondeada, leyenda y la paleta suave. Si los datos no sirven, el bloque queda visible con el motivo (`⚠ Valor no numérico en «Enero»: mucho`). Sin dependencias: lo dibuja el propio escritorio. La lectura del bloque la escribió qwen2.5-coder: no separaba por `;`, corregido. Dos bloques de código seguidos ya no se funden en uno. Captura: `docs/images/nota-graficas.png`. 137 pruebas correctas.
- ISO del 3 de noviembre (10:09, SHA-256 `c1cdab8a…c183`, incluye todo lo anterior): grabada con `write-usb.sh` en una imagen de USB de 6 GiB y arrancada en QEMU como `usb-storage`. Escritorio correcto a 1360×850; Super+Intro abre Foot; `/home/prosperus` montado desde `PROSPERUS_DATA` (loop); un archivo creado en la sesión sigue en la partición tras apagar por ACPI y el ext4 queda limpio. Grabar el USB real necesita sudo (udisks pide la contraseña de administrador). Copia de lo que había en el `PROSPERUS_DATA` del USB (home y registro del portátil) en `out/usb-backup-2026-11-03`.

## 3 de noviembre de 2026 · USB con el sistema entero persistente

- La partición `PROSPERUS_DATA` (todo el espacio libre del USB) guarda ahora también la capa de cambios del sistema: lo que se instala con dnf, los controladores (akmod-nvidia) y `/etc` se conservan. Módulo dracut `prosperus-persist`: tras encontrar el medio Live monta la partición por loop y apunta la capa overlayfs de dmsquash-live a `sistema/<versión de la ISO>`. La carpeta personal, Flathub, las redes y el registro siguen aparte, para sobrevivir a una ISO nueva; la capa del sistema de otra versión se descarta. `sistema/REINICIAR` vuelve al sistema recién grabado. dnf no instala núcleos (el arranque usa el de la ISO). Detalles: `docs/PERSISTENCIA.md`.
- Salvaguardas: solo se usa una `PROSPERUS_DATA` que sea partición del disco `PROSPERUS_LIVE`; con fsck sin reparar o menos de 1 GiB libre, el sistema arranca en RAM.
- Probado en QEMU con el USB (`usb-storage`) y un disco interno falso (NVMe con ESP, swap y raíz ext4 «bazzite»): el disco interno no se monta ni se activa su swap, y su SHA-256 es idéntico tras dos arranques. `cowsay` instalado con dnf y un cambio en `/etc` siguen tras reiniciar; una capa antigua plantada se descarta; ext4 limpio tras apagar.
- Super+Intro abría la terminal y además Buscar: Sway se quedaba el Intro y el escritorio veía Super sola. En Sway, Super sola la decide ahora Sway (`bindsym --release Super_L nop prosperus-search`). Comprobado en la VM: Super+Intro solo abre la terminal; Super sola abre Buscar también con la terminal delante. 138 pruebas correctas.
- ISO de las 12:40, SHA-256 `14df164f9200…`.
- Dos pantallas en el HP: el HDMI cuelga de la NVIDIA (card0-HDMI-A-1) y la pantalla interna de la AMD. `prosperus-session` usaba solo la gráfica de arranque, así que el HDMI no podía salir, y con el controlador propietario cargado Sway no arranca sin `--unsupported-gpu` (pantalla negra tras instalarlo). Ahora espera a todas las gráficas con controlador (la NVIDIA solo si `modinfo nvidia` existe), las pasa a Sway con la de arranque primero, añade `--unsupported-gpu` si el módulo nvidia está cargado y lo anota en `journalctl -t prosperus-diag`. `/etc/modprobe.d/prosperus-nvidia.conf`: `nvidia-drm modeset=1 fbdev=1`. Comprobado el cálculo en el propio HP con Bazzite (`/dev/dri/card1:/dev/dri/card0`, `--unsupported-gpu`) y la ISO en QEMU (una gráfica, sin opciones, escritorio correcto, disco interno falso intacto). `kernel-devel` del núcleo de la ISO (7.2.15-200) está en los repositorios, así que akmods puede compilar. Falta comprobar en el portátil el HDMI con el controlador instalado. ISO de las 12:52, SHA-256 `1f385b314214…`.

## 3 de noviembre de 2026 · Primera prueba en el portátil

- Apagar y reiniciar preguntaban «¿Apagar la VM?» y, en un equipo real, se negaban («solo disponibles en la VM»). Ahora dicen «el equipo» y funcionan fuera de una VM (siguen limitados a la sesión de la imagen).
- Foot se abría en `/` (greetd arranca la sesión en la raíz). La sesión entra en la carpeta personal y Super+Intro, «Consola (Foot)» de Aplicaciones, Wi-Fi, Bluetooth y el asistente de controladores abren `prosperus-terminal`: Foot en la carpeta del proyecto que se ve en el escritorio.
- Las ventanas ya no son siempre verdes: el escritorio publica la paleta del proyecto (sale del fondo) en `$XDG_RUNTIME_DIR/prosperus` (`theme_state.py`). Foot (fondo, texto y barra), el asistente Claude, las notificaciones (mako, con `makoctl reload`), Instalar programas y Fondos toman ese tono. Ramas ya lo hacía.
- Nota nueva «Bienvenida/Recursos/Código y gráficas»: cómo escribir un bloque ` ```python ` y una gráfica; los colores salen en la vista de lectura, no en «Editar». 142 pruebas correctas.
- En el portátil, la nota de código se escribió con `'''python` (comillas simples: la invertida es tecla muerta en el teclado español) y salía como texto. Ahora `'''lenguaje` y `´´´lenguaje` abren y cierran bloques igual que ` ``` ` (`loose_fences`); dentro de un bloque ` ``` ` de verdad no se tocan (docstrings). 143 pruebas correctas.
- Ctrl+Alt+T también abre la consola, por si la Super de un teclado programable no llega como Super.
- Registro del USB: en toda la sesión Foot solo se abrió una vez, la del asistente de controladores (instaló akmod-nvidia). Super+Intro y «Consola (Foot)» no llegaron a lanzarlo: pendiente de saber cómo se intentó.
- ISO de las 16:36, SHA-256 `2223aaaa42e3…`. Probada en QEMU: Super+Intro y Ctrl+Alt+T abren Foot en la carpeta del proyecto (`~/Proyectos`, `~/Proyectos/Laboratorio` tras Ctrl+3) con su tono (azulado en Laboratorio); la consola responde (`ls`, `pwd`). Una nota con `'''python` sin cerrar se ve con colores.
- Marcos de ventana a juego con el fondo (`window_frame.py`):
  - El borde va en el color de resalte de la paleta del fondo, con un degradado más intenso en las esquinas.
  - Dos esquinas opuestas llevan filigrana con el estilo procedural de las ramas del proyecto (árbol de la vida, art déco o art nouveau, más los ajustes de «Ramas»).
  - Lo llevan las notas, las ventanas propias (Ramas con la paleta de su carpeta; Fondos e Instalador con la publicada) y todos los diálogos del escritorio (Explorar, Papelera, Atajos, avisos…), que se visten solos al aparecer. El remate bajo el título usa el mismo color.
  - El escritorio publica también los rasgos de las ramas en `theme.json` (sin imágenes propias), para que los programas aparte dibujen el mismo estilo.
  - Foot lleva un borde de 2 px en el color de resalte.
  - Con alto contraste, borde simple sin filigrana.
  - Capturas: `docs/images/marcos-notas.png` (el mismo marco con dos fondos) y `docs/images/marco-ramas.png`. 147 pruebas correctas.
- GIMP fuera de la imagen base, a petición. Si hace falta, se instala desde Flathub con «Instalar programas» (se conserva con el USB persistente).

## 2026-11-03 — Botones y diálogos a juego

- Los diálogos de Qt salen en español (Sí/No, Aceptar/Cancelar, Guardar…): se carga `qtbase_es` en todas las
  apps y la imagen base añade `qt6-qttranslations`.
- Fuera el icono azul de los avisos; botones de diálogo centrados.
- Flechas SVG del color del tema en desplegables, casillas numéricas y botones con menú; marca ✓ en las casillas.
- Deslizadores y botones de herramienta con estilo propio en todo el escritorio.
- Las ventanas con marco dejan 22 px de margen: la filigrana de las esquinas ya no pisa Cerrar/Instalar.
- Instalar programas usa el estilo común (botones y buscador como el resto).

## 2026-11-03 — Instalador con recomendadas

- «Instalar programas» abre con un catálogo de recomendadas por categorías (`recommended.py`): utilidades
  (Input Remapper, Piper, Solaar, OpenRGB, Mission Center, LocalSend, KeePassXC…), multimedia (Jellyfin, VLC,
  OBS…), ingeniería, juegos e internet. Ids de Flathub y paquetes de Fedora comprobados.
- Las ya instaladas llevan ✓. Input Remapper y Piper activan su servicio (`input-remapper`, `ratbagd`) al instalarse.
- Buscar con el campo vacío o el botón «Recomendadas» vuelve al catálogo.
- La imagen base instala también los textos en español (`%_install_langs en_US:es_ES:es`): el contenedor de
  Fedora solo traía inglés y `qtbase_es.qm` no llegaba a la ISO.
- Al quitar GIMP de la imagen base se fue también DejaVu Sans Mono (venía con él): Foot salía con letra proporcional y un aviso. `dejavu-sans-mono-fonts` va ahora explícito en la imagen base (también la usan los bloques de código de las notas).
- ISO de las 21:56, SHA-256 `2615889e185a…`, con todo `main`: probada en QEMU (Ctrl+3 → Laboratorio, Ctrl+Alt+T abre Foot allí con letra monoespaciada, tono azulado y marco del color de resalte).
- Consola Foot al 80 % (antes 60 %), barra de título incluida: se leía mal sobre el mapa.
- Input Remapper en la imagen (servicio activado) con el mismo preajuste que en Bazzite: «DosFlechas», el botón lateral 276 (BTN_EXTRA) del Razer Naga Trinity hace de clic izquierdo, cargado solo al entrar. Los preajustes van en `/usr/share/prosperus/input-remapper-2`; la sesión los copia a `~/.config/input-remapper-2` si no existe y lanza `input-remapper-control --command autoload` (registro: `journalctl -t prosperus-remapper`).

## 3 de noviembre de 2026 · Escritorio estilo Arch

- SwayFX (COPR oficial `swayfx/swayfx`, sustituye a Sway con `dnf swap`): desenfoque detrás de las ventanas translúcidas, esquinas de 12 px y sombra; el escritorio queda recto (`smart_corner_radius`) y la píldora sin sombra.
- Consola: prompt en dos líneas (carpeta, rama de git, ❯ verde o rojo), `ls`/`ll`/`tree` con eza, `cat` con bat y fastfetch al abrir (`/etc/profile.d/prosperus-shell.sh`). btop con los colores de la consola.
- Super+L bloquea con swaylock sobre el fondo del proyecto desenfocado y oscurecido, anillo en los colores del tema (`lock_screen.py`); swayidle bloquea a los 10 min, apaga la pantalla a los 15 y bloquea antes de suspender. El usuario Live pasa a no tener contraseña (antes bloqueada): Intro desbloquea hasta que se ponga una con `passwd` (sudo ya era sin contraseña).
- Impr Pant / Mayús+Impr Pant: captura entera o de zona (grim, slurp) en Imágenes/Capturas, copiada al portapapeles y con aviso. Super+V: historial del portapapeles (cliphist) en fuzzel con los colores del proyecto.
- Código base de la consola, el desenfoque y las capturas: qwen2.5-coder (local), con correcciones (color del ❯, imagen oscurecida sin desenfocar, salida con error en un subshell, una comilla).
- SwayFX se instala con `dnf install --allowerasing swayfx` (`dnf swap` chocaba con sway-config-upstream). ISO de las 23:25, SHA-256 `d37ca413f960…`, probada en QEMU: SwayFX 0.6 en marcha (desenfoque detrás de Foot, esquinas, sin barra de errores de configuración); prompt, eza y fastfetch; Impr Pant guarda la captura y avisa; Super+L bloquea con el fondo desenfocado e Intro desbloquea; Super+V muestra el historial (la captura aparece).

## 3-4 de noviembre de 2026 · Mejoras de interfaz aprobadas

- SwayFX atenúa las ventanas sin foco (`default_dim_inactive 0.18`), salvo el escritorio y la píldora.
- Barra en pantalla para volumen y brillo (wob) con los colores del proyecto, en las teclas multimedia (`prosperus-osd`, escrito por qwen2.5-coder). Si el proyecto cambia de tono, wob se reinicia con su nueva configuración sin perder valores (la tubería queda abierta en la sesión).
- Iconos Papirus (oscuro) en Aplicaciones y en GTK, y cursor Bibata Modern Classic (descargado con SHA-256 fijo) en Sway, GTK y Qt (`XCURSOR_THEME`).
- fastfetch con logo propio (centro y ramas del mapa de proyectos, `/usr/share/prosperus/fastfetch-logo.txt`) desde `/etc/xdg/fastfetch/config.jsonc`.
- Super+Mayús+S (como Spectacle en Bazzite): zona con slurp y editor swappy (flechas, recuadros, texto) con el resalte del proyecto; al cerrarlo se guarda en Imágenes/Capturas y se copia. Satty no está en Fedora; Spectacle arrastra KDE. Impr Pant y Mayús+Impr Pant siguen igual.
- Aplicaciones externas en oscuro: adw-gtk3-dark para GTK3, `color-scheme='prefer-dark'` por dconf (lo lee libadwaita y Flatpak a través de xdg-desktop-portal-gtk), iconos y cursor también en dconf. xdg-desktop-portal-wlr para compartir pantalla y capturas (navegador, OBS); `/etc/xdg-desktop-portal/portals.conf` elige gtk por defecto y wlr para ScreenCast/Screenshot. Sway pasa WAYLAND_DISPLAY y demás al bus de la sesión.
- Iconos en eza (`--icons=auto`): símbolos de Nerd Fonts 3.5.1 (descarga con SHA-256 fijo, con su regla de fontconfig) como fuente de respaldo de Foot; la letra sigue siendo DejaVu Sans Mono.
- Panel Sistema: selector de salida de sonido (`wpctl status` → `wpctl set-default`, solo si hay más de una) y, si algo suena o está en pausa, «Reproduciendo» con anterior, reproducir/pausa, siguiente y la pista (playerctl). Teclas multimedia de reproducción en Sway. `parse_sinks` la escribió qwen2.5-coder (no veía los títulos con «├─»; corregido).
- Archivos por proyecto (sin carpetas globales de Descargas o Imágenes): las descargas llegan a `~/.local/share/prosperus/entrantes` (XDG_DOWNLOAD_DIR de la sesión; los navegadores guardan ahí sin preguntar) y el escritorio las mueve, cuando terminan (sin `.part`/`.crdownload` y con tamaño estable), al proyecto que se ve, en la carpeta de su tipo: Imágenes, Documentos, Vídeos, Audio, Comprimidos (`file_routing.py`, `incoming.py`). La carpeta del tipo se crea con el primer archivo y nunca se sobrescribe (« (2)»). En «Tus proyectos» va al último proyecto abierto; si no hubo ninguno, espera. Extensión desconocida: se pregunta la carpeta (una existente o una nueva) y se recuerda para todos los proyectos en `~/.config/prosperus/destinos.json`; Controles › «Destinos de archivos…» permite olvidarla. Las capturas (Impr Pant, Mayús+Impr Pant, Super+Mayús+S) van a `<proyecto>/Capturas`. `xdg-user-dirs` ya no crea Escritorio, Música… en la carpeta personal. Mover entre proyectos sigue siendo copiar/pegar (son carpetas normales). `extension`, `folder_for` y `unique_target`: qwen2.5-coder, correctas a la primera. 167 pruebas correctas.
- Las descargas no llegaban a la carpeta de entrada en navegadores: GLib (Firefox, Zen, también en Flatpak) lee `~/.config/user-dirs.dirs`, no la variable, y `xdg-user-dirs-update --set` fallaba. La sesión escribe ahí XDG_DOWNLOAD_DIR (comprobado con `GLib.get_user_special_dir`). Zen (Flatpak) ya tiene `xdg-download`; además un override del sistema le da la carpeta de entrada. Encontrado de paso: `~/.config` de la imagen era de root (lo creaba `install -D` del ajuste de btop), así que ni Input Remapper ni user-dirs podían escribir allí; ahora se hace `chown -R` de la carpeta personal.
- Clasificar a mano, nunca solo (en la raíz se dejan notas y archivos a propósito): clic derecho sobre archivos, «Mover a Imágenes» (o «Mover a su carpeta…» si son de varios tipos o desconocidos, con el diálogo de destino que se recuerda); clic derecho en el fondo, «Ordenar archivos sueltos…»: lista con casillas y destino editable por fila, sin mover nada hasta aceptar. Notas .md, carpetas y extensiones desconocidas salen desmarcadas; no entra en subcarpetas ni toca el fondo ni las carpetas de tipo. Mismo « (2)» y `destinos.json`. `sort_plan` a mano (Ollama devolvió error 500 durante la compilación de la ISO). 171 pruebas correctas.
- ISO de las 00:19 probada en QEMU: un PDF dejado en la carpeta de entrada acaba en `Laboratorio/Documentos`; `user-dirs.dirs` correcto y `~/.config` del usuario; wob en marcha con el tema; Super+Mayús+S abre la selección de zona; `ls` con iconos. Fallo: fastfetch solo dibujaba el logo (sin lista de módulos en la configuración); corregido.
- ISO de las 00:35, SHA-256 `bca455fefd0d…`: fastfetch con logo y datos; resto como la anterior.
- ISO del 4 nov a las 07:43, SHA-256 `cd13a59d6403…`: main con los comentarios del tarjetero (sin cambios de comportamiento); 171 pruebas en verde.

## 2026-11-04 — Tonos y fondos por horas

- `tones.py`: 23 tonos en tres grupos. Contraste (blanco y rojo, papel y azul tinta, marrón y verde, negro y
  amarillo, azul marino y naranja, granate y crema, verde bosque y dorado, violeta y menta, carbón y turquesa),
  Suavidad (verdes, azules, amarillos, rojos, lavanda, turquesas, terracota, rosas, piedra) y Momentos del día
  (amanecer, mediodía, atardecer, ocaso, noche). Cada tono da la paleta de la interfaz y una receta de color.
- `recolour.py`: recolorea el fondo conservando su diseño (telas, estampados, luces): busca las dos familias de
  tono de la imagen y cambia tono y saturación, no la luz; mezcla suave entre familias. Caché en
  `~/.cache/prosperus/fondos/` (unos 2 s la primera vez por imagen y tono).
- `wallpaper_schedule.py`: horario por carpeta en `.fondo.json` (tono por defecto, fundido en minutos, horas
  con imagen y tono). Las imágenes de cada hora se copian como `wallpaper-HH.*` y no salen en el mapa.
- El escritorio mira la hora cada 15 s y funde la imagen anterior con la nueva durante el fundido (30 min por
  defecto); la paleta cambia a mitad del fundido.
- Fondos (selector): miniaturas, «Fondo actual», tono con vista previa, horario (añadir/quitar hora) y fundido.

Ideas para más adelante:
- Fondo animado (la tela ondulando un poco): deformación suave de la imagen a 20-30 fps. Gasta CPU/GPU de forma
  continua; solo como opción para equipos con GPU, desactivada en portátiles y con batería.

## 2026-11-04 — Fondo animado (opcional) y panel Sistema con los colores del proyecto

- `living_wallpaper.py`: capa OpenGL bajo las tarjetas; un shader ondula muy despacio la tela del fondo (solo
  donde hay dibujo; lo oscuro, donde va el texto, queda quieto), con un brillo que se mueve con la onda. Hace
  también el fundido de los fondos por horas y el velo. 30 fps solo en la GPU: las tarjetas no se repintan.
  Se para al ocultarse. Probado en Sway sin pantalla (grim): tarjetas y zona oscura idénticas entre fotogramas.
- Sistema › Fondo › «Fondo animado» (apagado por defecto; se recuerda). `PROSPERUS_NO_LIVING=1` lo impide.
- El panel Sistema y su menú se reestilan en cada cambio de proyecto/tono (antes se quedaban en verde).

## 2026-11-04 — Versión sobre Arch Linux

- ISO Live sobre Arch (`image/arch/`, `scripts/build-iso-arch.sh`, `docs/ARCH.md`); el escritorio
  detecta Arch o Fedora (`distro.py`). Comprobada solo en QEMU sin red.
- **Pendiente:** probar los dos sistemas (Arch y Fedora) en hardware real. Lista de pruebas mínimas en
  `docs/PRUEBAS-MINIMAS.md`, para ir marcando.
- Primera prueba de la ISO de Debian: las flechas no movían la selección del mapa (el foco se quedaba
  en el QScrollArea al arrancar) y btop abría una consola sin título ni forma visible de salir. El mapa
  toma el teclado al mostrarse; btop sale en Aplicaciones como «Monitor del sistema» con el título
  «Q para salir» (`/usr/share/prosperus/xdg/applications/btop.desktop`, primero en XDG_DATA_DIRS).
  Intro en Aplicaciones ya no lanza el programa dos veces. Comprobado en QEMU.

## 2026-11-04 — Panel táctil, Esc para volver y atajos de ventana

- Panel táctil (todas las ISO): Sway lo dejaba sin «tocar para hacer clic», así que dos toques no abrían
  nada. Ahora tocar es clic (dos toques = doble clic), dos dedos = clic derecho, tocar y arrastrar,
  sin cursor al escribir y aceleración adaptativa. Sin probar en hardware real.
- Selección del mapa: el ratón quieto encima de una tarjeta la dejaba resaltada mientras las flechas
  resaltaban otra. Ahora solo se resalta una (la del foco); pasar el ratón por encima la selecciona.
- Esc vuelve a la carpeta anterior (antes de eso cierra la nota enfocada o el tarjetero); en el
  explorador sube una carpeta y, en Todos los proyectos, lo cierra.
- Ventanas: Super+↑ amplía/restaura (comparte estado con la píldora), Super+↓ minimiza, Alt+F4 cierra;
  siguen Super+M, Super+Q y Super+F. Configuración comprobada con Sway sin pantalla. 194 pruebas correctas.
- Cursor: Bibata no gustaba; ahora Breeze (el de KDE) desde los repos de cada sistema
  (`breeze-cursor-theme` en Fedora y Debian, `breeze-cursors` en Arch). ISO de Debian de las 19:03.

## 2026-11-04 — Cerrar Buscar, panel Ramas más claro y ventanas deformables

- Buscar (Super) tiene botón ✕ arriba a la derecha (también se cierra con Esc o Super).
- Ramas: las barras «Art déco / Art nouveau» pasan a «Geométrica» y «Ondulada», cada una con una
  línea debajo que dice qué dibuja; «Trazo» (curvatura, grosor, opacidad) va aparte. En automático las
  barras muestran lo medido en el fondo y un aviso explica que hay que desmarcarlo para moverlas.
- Hueco entre aplicaciones (`window_gaps.py`): arrastrarlo mueve ese borde en todas las ventanas que lo
  comparten (como un separador de mosaico); el margen exterior agranda o encoge una sola. Mínimo 200×140.
  Doble clic en el fondo del escritorio minimiza las aplicaciones del proyecto (Super+D las devuelve).
  Al abrir o cerrar una aplicación, Fibonacci vuelve a repartirlas. Solo en la pantalla de PrOSperus:
  en las otras el fondo es swaybg y no recibe clics.
- Super+arrastrar (mover) y Super+clic derecho (tamaño) ya no abren Buscar al soltar Super: el escritorio
  descarta la búsqueda si una aplicación cambió de geometría en el último segundo y medio.
  Super+Alt+flechas cambian el tamaño con el teclado. Configuración validada con `sway -C`.
- Pruebas con árbol de Sway simulado; sin probar en hardware real ni con dos monitores. 203 pruebas correctas.

## 2026-11-04 — 0.5.0: segunda pantalla, notas en la carpeta actual e Inicio

- Pantallas secundarias: al arrancar, cada una abre una consola (app_id `org.prosperus.PantallaN`,
  colocada con una regla `for_window` en caliente para no robar el foco). Las ventanas nuevas se reparten
  en Fibonacci en la pantalla en la que aparecen; al cerrar se reorganizan todas. Comprobado en Sway
  sin pantalla con dos salidas: escritorio en una, consola en la otra. `PROSPERUS_NO_SECONDARY_TERMINAL=1`
  lo desactiva. Pendiente: el mapa con notas en la segunda pantalla (haría falta otra ventana del escritorio).
- Nueva nota/carpeta: `QComboBox.findData` no encontraba objetos `Path` y proponía siempre la raíz.
- «Tus proyectos» → Inicio (raíz) y Proyectos (tarjetero). Versión 0.5.0. 205 pruebas correctas.
- `output_of`/`other_outputs` los escribió qwen2.5-coder:7b; `output_of` solo miraba un nivel y se corrigió.

## 2026-11-04 — Alt+Tab con las ventanas a la vista, Tab dentro de cada ventana y botones para los atajos

- Alt+Tab / Alt+Mayús+Tab (Sway: `nop prosperus-switch`): el escritorio enseña las aplicaciones y notas
  abiertas del proyecto, minimizadas incluidas (apagadas a la mitad), con la última usada primero; al soltar Alt abre la elegida
  (también Intro o clic; Esc cancela). Una minimizada vuelve a su sitio. `window_switcher.py`.
  Super+Tab sigue pasando de proyecto.
- Tab dentro de una nota, del tarjetero o del panel Sistema recorre solo sus controles y da la vuelta
  (`focus_trap.py`); antes saltaba a los nodos del mapa, o a las entradas del menú en el panel Sistema.
- Solo con teclado → ahora también con ratón: fila «Sesión» en Sistema (Bloquear, Captura, Zona,
  Portapapeles, Escritorio) y botones «← Atrás» / «Adelante →» del historial junto a «↑ Subir».
- Solo con ratón → ahora también con teclado: Super+↓ / Super+↑ minimizan y amplían la nota enfocada
  (antes solo los puntos de la nota).
- Sin cambiar: reordenar nodos del mapa arrastrando y arrastrar archivos al mapa siguen siendo solo de
  ratón (con teclado hay Ctrl+C/V); los puntos de ventana no son tabulables porque tienen atajo.
- Base de `focus_trap.py` y `window_switcher.py` escrita por qwen2.5-coder:7b (local); corregidos un
  import que faltaba, el recorte del nombre y Escape. Comprobado sin pantalla con el escritorio real;
  207 pruebas correctas. ISO de Debian de las 22:35 (SHA-256 `3e22e652…eee3`) en QEMU: con Alt pulsado sale el selector
  (dos consolas, la minimizada apagada), Tab cambia la marcada y al soltar Alt se abre. Sin probar en hardware real.
