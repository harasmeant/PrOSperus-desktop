# Pantallas y distribución · 0.4.0-dev

Referencia confirmada por Nicolás el 30 de octubre de 2026: espiral Fibonacci.
El objetivo es un sistema que gestione aplicaciones reales y conserve la experiencia de proyectos de PrOSperus.

## Controles disponibles

Desde **Controles → Pantallas y distribución**:

- Elegir pantalla y consultar dimensiones lógicas, escala y frecuencia.
- Elegir espiral Fibonacci, columnas o ventana principal centrada.
- Ajustar separación, proporción principal y anchura máxima centrada.
- Guardar perfiles separados para pantalla estándar, 21:9 y 32:9.
- Previsualizar distintas cantidades de ventanas.
- Organizar notas visibles y deshacer mientras el diálogo siga abierto, conservando contenido y cambios sin guardar.

La espiral alterna izquierda, arriba, derecha y abajo. Cada corte toma la mitad del espacio restante; se puede ajustar el primero. Principal centrada usa laterales a partir de tres ventanas; con dos divide izquierda/derecha. Si no caben ventanas legibles, se rechaza la distribución antes de moverlas.

Los perfiles **no cambian resolución, escala ni frecuencia**, ni se aplican automáticamente al abrir ventanas. Las notas se distribuyen dentro del mapa, en la pantalla de PrOSperus.

## Aplicaciones reales: integración experimental

**Organizar aplicaciones** requiere Sway y `SWAYSOCK`. Organiza únicamente el espacio visible de la pantalla elegida, por orden de creación, excluyendo PrOSperus por su identificador. Desactiva pantalla completa y coloca ventanas como flotantes.

Se comprueban geometrías finales. Algunos clientes redondean su tamaño: se admite y comunica si conservan su origen, caben en la zona y siguen siendo legibles. Si desaparecen o rechazan el tamaño, se comunica el resultado incompleto. No hay transacción ni deshacer de aplicaciones: las órdenes anteriores pueden haberse aplicado.

**La ISO publicada v0.3.2-live.1 sigue usando Cage.** No incluye estos cambios. GNOME tampoco ofrece este adaptador. No se ha cambiado el compositor del anfitrión.

## Verificación del 30 de octubre

- 69 pruebas locales satisfactorias, incluidas geometría, perfiles, conservación de texto, deshacer y errores del compositor.
- Sway aislado con pantallas virtuales 3440×1440 y 1920×1080: cuatro aplicaciones Wayland reales en las tres distribuciones, geometrías exactas y ventana de la otra pantalla sin cambios.
- Cliente adicional con redondeo a celdas: tamaño ajustado detectado y comunicado.
- Captura real de controles Qt en Wayland. Una revisión posterior del guion mejora la captura modal; repetirla quedó pendiente por fallo de la revisión automática de permisos al agotarse su cuota.
- 5120×1440, pantalla vertical y origen negativo cubiertos por pruebas geométricas; no equivalen a monitores físicos validados.

Pruebas locales:

```sh
PYTHONPATH=desktop QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -q
```

Laboratorio: `image/Containerfile.window-tests` y `scripts/check-window-session.py`. Requiere primero la imagen local `localhost/prosperus-live:dev`. Ejecutar como usuario 1000 con `--userns=keep-id`, sin red, `--cpus=2 --memory=768m --memory-swap=768m`, repositorio montado en `/source:ro`, evidencia escribible en `/output` y `PYTHONPATH=/source/desktop`. No montar sockets ni dispositivos gráficos del host. Evidencia local: `out/window-layouts/verification.json` y capturas.

## Siguiente bloque de sistema

Integrar una sesión completa: mapa permanente debajo de aplicaciones, foco, atajos globales, lanzador, cambio entre ventanas y espacios por proyecto. Después, conexión/desconexión de pantallas, recuperación de disposición y resolución/escala con confirmación y reversión. Generar y probar una nueva ISO con esa sesión.

Persistencia, instalador, actualizaciones y hardware siguen pendientes. Esta distribución manual es una base comprobada, no un gestor completo ni una nueva ISO terminada.

Referencias: [Fibonacci de dwm](https://dwm.suckless.org/patches/historical/fibonacci/) y [IPC de Sway](https://github.com/swaywm/sway/blob/master/sway/sway-ipc.7.scd).
