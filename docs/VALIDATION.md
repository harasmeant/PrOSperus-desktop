# Validación

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
