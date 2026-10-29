# Historial

## 0.3.2-dev — 2026-10-29 · Arranque único en Fedora Live

- `iniciar.sh` comprueba el Python del sistema y, si no puede importar Qt,
  reutiliza automáticamente `/tmp/prosperus-runtime` cuando pertenece al usuario
  y contiene PySide6 funcional. Se conserva la selección explícita mediante
  `PROSPERUS_PYTHON` y los argumentos `--root`.
- Si falta el entorno tras reiniciar el Live, el diagnóstico explica cómo
  reconstruirlo. El lanzador no instala paquetes automáticamente.
- Lanzador disponible también como archivo suelto para sustituir el de v3.1
  sin reemplazar notas ni volver a importar proyectos.

## 0.3.1-dev — 2026-10-29 · Búsqueda de contenido y diagnóstico de arranque

- Búsqueda por nombre, ruta y texto guardado de los Markdown en mapa y
  explorador. El tarjetero también encuentra proyectos por el contenido de
  sus notas. Mantiene coincidencias sin tildes/mayúsculas y prioriza nombres.
- Una nota ilegible, demasiado grande o eliminada durante la búsqueda no
  impide encontrar las demás. Se mantienen los límites de carpetas y lectura.
- El lanzador conserva el error de importación y muestra el espacio en `/`.
  Explica los límites de Fedora Live y el fallo de DNF por falta de espacio.
- Paquete `prosperus-demo-v3.1.tar.gz`, separado del anterior; no cambia el
  tamaño del sistema Live ni instala dependencias automáticamente.

## 0.3.0-dev — 2026-10-29 · Proyectos, portapapeles y teclado

- Nuevo proyecto explícito en la cabecera y el tarjetero; importar proyectos
  existentes conserva originales, subcarpetas y adjuntos.
- Selección simple/múltiple, doble clic e Intro para abrir, menú contextual,
  copiar/pegar/duplicar y arrastrar archivos locales al mapa. Copias en segundo
  plano, nombres alternativos ante colisiones y retirada de copias incompletas.
- Atajos de archivos respetando los editores de texto, navegación por historial,
  F1, F5, F11 y Ctrl+Espacio. Super y sus combinaciones responden cuando el
  compositor las entrega; la demo no modifica los atajos globales de GNOME.
- Controles de volumen, reproducción y brillo mediante herramientas de la
  sesión, con capacidades ausentes desactivadas. Teclas multimedia atendidas
  por PrOSperus solo en su sesión propia.
- Paquete Fedora v3 separado de v2. Sigue pendiente la paridad completa con
  un escritorio: gestión global de ventanas, renombrar/mover/eliminar con
  actualización de enlaces, persistencia y validación de la imagen de sistema.

## 0.2.0-dev — 2026-10-28 · Escritorio independiente

- Recuperación de la referencia de Obsidian: fondos y paletas por proyecto,
  tarjetero vertical superpuesto, mapa con tarjetas y conexiones curvas,
  notas flotantes con fondo heredado y barra contextual desplazable.
- Edición Markdown con vista previa y guardado explícito; detección de cambios
  externos y aviso al cerrar con modificaciones sin guardar.
- Creación de notas y carpetas; explorador con búsqueda de notas.
- Catálogo y lanzamiento de aplicaciones mediante GIO con favoritos globales.
- Paquete de prueba para Fedora con ejemplos, sin datos personales ni cambios
  en la sesión de escritorio. 27 pruebas locales y verificación del paquete.
- No incluye todavía paridad del gestor de archivos de Obsidian, recuperación
  de sesiones ni aplicaciones como nodos del proyecto. Prueba manual en la VM
  pendiente. Detalles en `docs/WORKLOG.md` y `docs/FEDORA-DEMO.md`.

## 2026-10-28 — Licencia y contribuciones

- Adopción de GNU GPLv3 exclusivamente (`GPL-3.0-only`) para el código y material original, incluido el prototipo propio de `v0.0`.
- Política de contribuciones: modificaciones libres y selección de aportaciones por el responsable del repositorio oficial.
- Se conserva la etiqueta histórica `v0.0`; el texto de licencia se incorpora a la rama principal.

## 0.0 — 2026-10-27

Primera referencia pública del proyecto de distribución Linux.

- Prototipo de escritorio por carpetas en Obsidian.
- Mapas, notas flotantes, explorador y lanzador de aplicaciones Linux.
- Código Python/JavaScript/CSS, cuatro pruebas del lanzador y evidencia histórica de interfaz.
- Documentación de instalación, límites y evolución hacia el escritorio independiente.
- Ejemplos ficticios y nombres de paletas preparados para publicación.

Esta versión no incluye una imagen Linux arrancable. El plugin conserva su manifiesto interno `0.1.0`.
