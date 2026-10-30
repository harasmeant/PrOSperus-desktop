# Validación

## Escritorio independiente 0.3.2-dev — 29 de octubre de 2026

55 pruebas satisfactorias. El lanzador se prueba con intérpretes de sistema
y temporales disponibles, ausentes o sin Qt, respetando argumentos y selección
explícita. Además, una ejecución real con Python `-S` reproduce la ausencia de
PySide6 y verifica la selección automática de Essentials y el arranque gráfico
sin pantalla. La reparación propuesta para la copia v3.1 se aplica al script
exacto de su archivo y también arranca. Evidencia: `out/verification-v3.2.json`.
El usuario confirmó después el arranque de su copia v3.1 reparada y que la
búsqueda ya funciona sobre su carpeta importada. Esto no equivale a una prueba
manual de la detección automática del paquete v3.2.

## Escritorio independiente 0.3.1-dev — 29 de octubre de 2026

51 pruebas pasan con Qt del sistema y con PySide6 Essentials 6.12.0. Incluyen
búsqueda en nombres/rutas y cuerpos Markdown, tildes, varios términos, alcance
de carpeta, cambios guardados, notas ilegibles/grandes y límites de acceso.
La prueba de interfaz reproduce **impresora → Cursos 3D**: devuelve la portada
del proyecto aunque la coincidencia exista solo en una nota de una subcarpeta.

Diagnóstico de dependencias probado simulando importaciones fallidas y un
Fedora Live con 183 MiB disponibles. Los mensajes conservan el error concreto.
Paquete extraído: fuentes idénticas, sintaxis de los lanzadores válida, arranque
desde otro directorio con Essentials y `--root` externo, renderizado y búsqueda
por contenido correctos. Evidencia en `out/verification-v3.1.json`.

El usuario confirmó arranque de v0.3 e importación de una carpeta en su VM
con el entorno de Essentials en `/tmp`. La instalación RPM había fallado por
falta de espacio en el Live. No se ha confirmado manualmente el paquete v3.1,
ni reconstruido la imagen ni generado una ISO. La vía Essentials requiere
la sesión gráfica y bibliotecas del sistema; no es un paquete autocontenido.

## Escritorio independiente 0.3.0-dev — 29 de octubre de 2026

45 pruebas locales satisfactorias, incluidas las 27 anteriores. Las nuevas
comprueban copias sin sobrescritura, estructura/adjuntos, nombres repetidos,
permisos, rechazo de enlaces y archivos especiales, recuperación ante errores,
selección, portapapeles de archivos frente a texto, arrastre, creación de
proyectos, historial, Super solo frente a combinaciones y controles simulados.
Las pruebas no cambian volumen/brillo ni lanzan aplicaciones del anfitrión.

Capturas sin pantalla a 1360×850 y 900×650; tarjetero, explorador y panel de
controles revisados. El paquete v3 se mantiene separado de la descarga v2.
La comprobación del contenido y del lanzador se registra en
`out/verification-v3.json`.

El usuario confirmó que v0.2 funciona en su Fedora. No equivale a validar v0.3:
queda pendiente comprobarla allí, especialmente portapapeles con Archivos,
drag-and-drop, Wayland, Super y funciones multimedia. GNOME conserva sus atajos
globales. No se ha reconstruido ni validado la imagen de sistema con v0.3.

## Escritorio independiente 0.2.0-dev — 28 de octubre de 2026

```sh
PYTHONPATH=desktop QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

27 pruebas satisfactorias en el entorno local. Cubren modelo de archivos,
guardado y colisiones, fronteras de rutas, enlaces, interfaz de proyectos y
notas, fondos, navegación por teclado, barra desplazable y aplicaciones.
Las escrituras se prueban con carpetas temporales; los lanzamientos se simulan.

Se ha consultado además el catálogo GIO real sin abrir aplicaciones y se ha
verificado un paquete recién extraído ejecutando su lanzador desde otra carpeta.
Se han inspeccionado capturas Qt a 1360×850 y 900×650. La comprobación detallada,
los archivos de evidencia y el hash de la entrega están en `WORKLOG.md`.

Esta validación no incluye una prueba manual de la versión nueva dentro de
Fedora/Boxes ni una reconstrucción de la imagen Linux. La evidencia siguiente
corresponde al prototipo de Obsidian y se conserva como referencia histórica.

## Pruebas del lanzador

Con Python 3 y PyGObject/GIO disponibles:

```sh
python3 -m unittest discover -s prototype/obsidian -p 'test_*.py' -v
```

Las cuatro pruebas existentes comprueban el ID exacto de lanzamiento, el rechazo de aplicaciones desconocidas u ocultas, los fallos de lanzamiento y que la salida de un proceso gráfico no contamine la respuesta JSON. Usan dobles de prueba; no abren aplicaciones reales.

Para comprobar la sintaxis JavaScript, con Node.js instalado:

```sh
node --check prototype/obsidian/main.js
```

La automatización de GitHub ejecuta ambas comprobaciones. No sustituye una prueba visual dentro de Obsidian.

## Comprobación de la copia pública — 27 de octubre de 2026

Las cuatro pruebas del lanzador pasaron en la copia preparada para publicación. La sintaxis de `main.js` se comprobó con el analizador de Node.js (`vm.Script`). También se revisaron los enlaces relativos de la documentación y la ausencia de rutas personales y patrones comunes de credenciales.

## Evidencia histórica de interfaz

`evidence/validation-desktop-2026-10-27.json` conserva 23 comprobaciones satisfactorias del prototipo original: navegación, búsqueda, selección, operaciones con archivos, favoritos, lanzamiento y errores visibles. Registra también una apertura real de KCalc en el entorno del autor.

Es evidencia de una sesión local anterior a la publicación, no una garantía de compatibilidad con otros equipos. No se incluyen capturas personales ni se han repetido esas pruebas visuales al preparar el repositorio.

## Pendiente

Pruebas reproducibles de interfaz sobre una bóveda de demostración, compatibilidad entre versiones de Obsidian/Hover Editor, aislamiento por proyecto, persistencia entre reinicios y pruebas de la futura imagen Linux.

## ISO Live 0.3.2 · 2026-10-29

Arranque óptico UEFI real en QEMU/KVM (OVMF, 2 vCPU, 2048 MiB, sin red ni disco),
sesión Cage/PrOSperus, creación de proyecto y nota, guardado y búsqueda por
contenido verificados. Se conserva la captura en docs/images/iso-live-preview.png.
El usuario de sesión dispone de una copia editable de los ejemplos. La imagen
incluye Qt/GIO y systemd-pam. No se ha validado aún en Boxes ni hardware físico.

## 30 de octubre de 2026 · Fibonacci y ultrawide · 0.4.0-dev

Usuario confirma espiral Fibonacci. Añadidos motor geométrico compartido, perfiles estándar/21:9/32:9, vista previa, anchura centrada y organización reversible de notas. Adaptador Sway experimental limitado al espacio visible del monitor seleccionado, excluyendo PrOSperus. Comentarios explican coordenadas lógicas, protección de otras pantallas y confirmación asíncrona de tamaños.

69 pruebas locales correctas. Sway aislado: cuatro aplicaciones, tres distribuciones, dos pantallas; geometrías verificadas y segunda pantalla sin cambios. La prueba detectó redondeo de tamaños de terminales: ahora se comprueba el resultado y se comunica el ajuste dentro de la zona. Cliente restringido probado. Evidencia en out/window-layouts.

Captura Qt real inspeccionada. El guion posterior espera el mapeado de la ventana antes de abrir el diálogo modal; su repetición quedó bloqueada por agotamiento de cuota de revisión automática de permisos, no por un rechazo de seguridad. La ISO publicada no se cambia. Integración completa de sesión y nueva ISO pendientes. Detalles: WINDOW-LAYOUTS.md.
