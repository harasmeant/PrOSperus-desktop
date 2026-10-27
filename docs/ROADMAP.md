# Hacia una distribución orientada a proyectos

Esta hoja de ruta describe trabajo pendiente. No constituye una lista de funciones disponibles en 0.0.

## 0.0 — Referencia inicial

Prototipo de Obsidian, documentación pública, ejemplos y evidencia histórica de validación. La experiencia visual sirve de referencia para el escritorio independiente.

## Próximo hito — Decisiones y primera imagen de desarrollo

Elegir base Linux, arquitectura, soporte gráfico, toolkit y mecanismo de actualización. Fedora/KDE y una base atómica son candidatos; la elección no está cerrada. Versionar una receta reproducible y arrancarla en una máquina virtual, comprobando actualización y recuperación. Una imagen del sistema y una ISO instalable son entregables distintos.

## Escritorio independiente mínimo

Separar cinco responsabilidades:

1. Motor de archivos y proyectos: abrir carpetas, vigilar cambios, buscar y gestionar operaciones con colisiones y permisos.
2. Motor de conocimiento: Markdown, enlaces relativos, wikilinks, backlinks e índice reconstruible.
3. Interfaz: mapa, selector de proyectos, notas, fondos, explorador y estado por proyecto.
4. Integración con Linux: aplicaciones, ventanas y peticiones estructuradas a servicios locales.
5. Imagen: paquetes, sesión, primer arranque, actualizaciones y recuperación.

Sustituir las dependencias de Obsidian y Hover Editor. Conservar los documentos como fuente de verdad y tratar el índice como información reconstruible.

## Aplicaciones por proyecto

Añadir aplicaciones como nodos o accesos del árbol. Distinguir un acceso normal del sistema de un modo restringido. Los favoritos globales actuales no cumplen esta función.

Diseñar y comprobar el acceso efectivo de una aplicación Flatpak a los archivos de su proyecto, considerando enlaces simbólicos, portales, D-Bus, red y procesos ya abiertos. Una preferencia guardada en un proyecto no debe conceder permisos ni ejecutar aplicaciones automáticamente.

## Integración y uso real

Persistencia de ventanas, coordinación con aplicaciones externas, multipantalla, controles del sistema y primer arranque. Validar en VM y después en hardware secundario antes de considerar una instalación de uso diario.
