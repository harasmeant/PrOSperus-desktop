# PrOSperus desktop

**Versión 0.0 · Prototipo de escritorio orientado a proyectos · 27 de octubre de 2026**

Un proyecto para organizar el trabajo en Linux alrededor de carpetas, notas y aplicaciones. Cada carpeta se convierte en un escritorio visual con un mapa navegable, notas flotantes y una barra de tareas contextual.

La versión **0.0** conserva el prototipo funcional desarrollado como complemento de Obsidian y establece el punto de partida para una futura distribución Linux. **Todavía no incluye una ISO, una imagen de sistema ni un escritorio independiente.**

## Lo que ya funciona

- Escritorio por carpeta con mapa de archivos y subcarpetas.
- Selector lateral de proyectos, búsqueda y navegación por teclado.
- Notas flotantes mediante Hover Editor, minimización y recuperación durante la sesión.
- Explorador de la bóveda: crear, buscar, mover, renombrar y eliminar con las API de Obsidian.
- Fondos heredados por subcarpetas y paletas por proyecto.
- Buscador de aplicaciones Linux y favoritos globales; lanzamiento mediante GIO.
- Apertura de archivos Python en VSCodium mediante su protocolo de escritorio.

## Qué demuestra este proyecto

Diseño de una interfaz de trabajo, desarrollo en JavaScript y CSS, integración con aplicaciones Linux mediante Python/GIO, gestión de archivos y validación automatizada. La evolución hacia un escritorio independiente exige separar la interfaz, el motor de archivos y enlaces, la integración con Linux y la construcción de la imagen.

**Autor:** [Nicolás · harasmeant](https://github.com/harasmeant). Desarrollo iterativo con asistencia de IA. Las funciones implementadas y las propuestas futuras están documentadas por separado.

## Probar la versión 0.0

Consulta la [guía de instalación](docs/INSTALL.md). El complemento no necesita compilación. Se incluyen notas ficticias en `demo/` para explorarlo sin usar documentos personales.

## Estructura

- [`prototype/obsidian/`](prototype/obsidian/): código del prototipo y pruebas del lanzador.
- [`demo/`](demo/): pequeñas carpetas y notas de ejemplo.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): alcance de la futura distro y siguientes hitos.
- [`docs/VALIDATION.md`](docs/VALIDATION.md): comprobaciones y límites de la evidencia.
- [`docs/BASELINE.md`](docs/BASELINE.md): procedencia del estado 0.0 y ajustes para publicarlo.
- [`CHANGELOG.md`](CHANGELOG.md): historial de versiones.

## Límites actuales

El prototipo depende de Obsidian y Hover Editor. El mapa representa la estructura de archivos, no un grafo semántico. La disposición de las ventanas no se recupera automáticamente tras reiniciar. Los favoritos de aplicaciones son globales y no existe aislamiento por proyecto. La base Linux y el toolkit del escritorio futuro siguen pendientes de elección.

## Licencia

La licencia del código propio está pendiente de elección. La publicación del repositorio no concede por sí sola una licencia de reutilización. Obsidian, Hover Editor y las aplicaciones del sistema son dependencias externas y no se redistribuyen aquí.

---

**English:** PrOSperus desktop is a project-oriented Linux desktop experiment. Version 0.0 contains a working Obsidian prototype with folder maps, floating notes, a vault explorer and a Linux application launcher. A standalone desktop and a bootable Linux image are planned, not yet implemented.
