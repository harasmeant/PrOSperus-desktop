# Bugs a revisar

Lista de trabajo. Marca: `[ ]` abierto · `[x]` resuelto (anotar fecha y commit).
Al cerrar uno, pasar el detalle a `WORKLOG.md` y quitarlo de aquí si ya no aporta.

## Abiertos

- [ ] **Dos pantallas: parpadeo o pantalla integrada apagada** (2026-11-08).
  Equipo: HP, AMD Cezanne (card1, eDP-1 del portátil) + NVIDIA GTX 1650 Mobile con 550
  (card0, HDMI-A-1 Philips). Sway 1.10.1 + wlroots 0.18.2 de Debian; ya sin SwayFX.
  - Con la AMD dibujando: parpadean el ratón y la **mitad superior** del HDMI (copia AMD → NVIDIA).
  - Con `nvidia` en `~/.config/prosperus/graficas` (21:21): el HDMI se ve, pero la **eDP-1 queda
    apagada** (`swaymsg -t get_outputs`: `power: false`). En el journal: `eglQueryDmaBufModifiersEXT
    … Invalid format` y `Requested backend configuration failed, searching for valid fallbacks`:
    Sway no logra las dos a la vez y apaga la del portátil. Es la copia NVIDIA → AMD, que falla.
  - Hecho: `graficas` renombrado a `graficas.desactivado` (vuelve a dibujar la AMD; con la
    siguiente sesión, las dos pantallas). Siguiente prueba: `echo vulkan >
    ~/.config/prosperus/renderizador` (nuevo en `prosperus-session`; hay que instalarlo).
  - 22:26: `prosperus-session` instalado y `renderizador` = `vulkan`. Probado en Sway sin
    pantalla: wlroots arranca Vulkan en la AMD (`RADV RENOIR`). Falta cerrar sesión y ver el parpadeo.
  - 22:27: Vulkan no sirve con la 550. La NVIDIA no importa los búferes de la AMD
    (`getMemoryFdPropertiesKHR: ERROR_UNKNOWN`), el HDMI no se enciende y la sesión pasaba a
    GLES2 con la NVIDIA de principal, que apaga la eDP. Ahora `prosperus-session` reintenta
    primero GLES2 con la AMD de principal. `renderizador` renombrado a `renderizador.desactivado`.
  - 23:20, causa probable del parpadeo: wlroots 0.18.2 copia cada fotograma AMD → NVIDIA
    (`backend/drm/renderer.c`, `drm_surface_blit`) sin esperar a que la AMD acabe: GLES2 solo hace
    `glFlush` y no pasa ninguna sincronización. El controlador de NVIDIA no respeta la
    sincronización implícita, así que copia fotogramas a medio dibujar. La AMD dibuja de arriba
    abajo, y por eso parpadea la mitad superior y el cursor por software. La 0.19 sí sincroniza
    (`wait_timeline`), pero necesita syncobj en la NVIDIA, y con el 550 no lo hay (DRM_CAP_SYNCOBJ
    = 0 en card0; la AMD sí lo tiene). Salidas: a) parchear wlroots 0.18 para que espere al búfer
    de la AMD (`poll` sobre el dmabuf) antes de copiar; b) NVIDIA ≥ 555 (repositorio de NVIDIA:
    580/620) + Sway 1.12/wlroots 0.20 (forky). No probado aún en sesión real.
  - Elegida la b, con Sway 1.11 + wlroots 0.19.3 (snapshot.debian.org, compilados en trixie sin
    tocar sus bibliotecas; la 0.20 pedía libdrm, pixman y wayland nuevos). Paquetes en
    `/var/cache/prosperus-debs`, retenidos con `apt-mark hold`. NVIDIA 620.70.06 del repositorio
    de NVIDIA, que solo aporta los paquetes del controlador (`/etc/apt/preferences.d/prosperus-nvidia`).
    Volver atrás: `apt-mark unhold sway sway-backgrounds libwlroots-0.19`, borrar ese pin y el
    repositorio `cuda-*` de `sources.list.d`, y reinstalar `sway nvidia-driver nvidia-open-kernel-dkms` de trixie.
  Soluciones encontradas fuera: ver «Dos pantallas» en WORKLOG (búsqueda del 2026-11-08).

- [ ] **La pestaña Sistema no se ve completa** (2026-11-08). Menú `Sistema` (`shell.py:1198`,
  ventana en `shell.py:1505`): se corta por abajo. 2026-11-08: el panel va dentro de un área con
  desplazamiento que no pasa del alto de la pantalla (`quick_settings.scrollable`). Falta verlo.

- [ ] **Arrastre de ventanas** no funcionaba bien (zonas, inercia, intercambio).
  2026-11-08: simplificado. La ventana arrastrada queda libre donde se suelta y las demás
  cierran el hueco. Botón **«Patrón»** (junto a «Fibonacci», y al pasar a Fibonacci): notas y
  aplicaciones, también las libres, al hueco del patrón que tienen más cerca (`nearest_order`,
  menor recorrido total). 2026-11-09: al soltarla encaja en el hueco que tiene debajo (o el más
  cercano) y se intercambia con la que lo ocupaba (`slot_under`). Falta probarlo en la sesión real.

- [ ] Multipantalla: conectar y desconectar un monitor puede perder ventanas (sin probar).
  Necesita la prueba a mano: con ventanas en el HDMI, desenchufarlo y volver a enchufarlo.

- [ ] **Consola toda en blanco.** foot abre bash sin login (no lee `/etc/profile.d`) y el
  `~/.bashrc` de Debian no colorea con `TERM=foot`. 2026-11-08: fish en las tres imágenes,
  `prosperus-terminal` lo abre si está y `/etc/fish/conf.d/prosperus.fish` copia el prompt y
  los alias (instalado y comprobado el prompt). foot sustituido por kitty (consola, asistente
  Claude, tono del proyecto en `kitty.conf`). Falta probar kitty en el portátil.

## Pendiente de probar en la sesión real

Arreglado en código, sin comprobar a mano. Cerrar sesión antes de empezar.

1. **Ventanas:** arrastrar una a la izquierda y soltarla (encaja en ese hueco y se intercambia); botón
   «Patrón» y paso a Fibonacci (cada una al hueco más cercano); Super+flechas.
2. **Inicio (Super)** con la Papelera abierta detrás: debe abrirse.
3. **Diálogos:** cada uno con cabecera y botón de cerrar; Esc los cierra.
4. **Mover** una nota con enlaces relativos (en los dos sentidos) y abrirlos.
5. **Consola kitty + fish:** colores, prompt, alias; asistente Claude abre en kitty.
6. **Multipantalla:** con ventanas en el HDMI, desenchufarlo y volver a enchufarlo.
7. **Escritorio único** (rama `arreglo-escritorios-duplicados`): uno solo tras iniciar sesión y
   tras volver de suspender.
8. **Pantallas:** las dos encendidas, sin parpadeo, con el ratón moviéndose de una a otra.

## Resueltos

- [x] **`except Exception` que ocultaban errores** (2026-11-08, sin commit). Fuera `input_capture.py`,
  `appearance_settings.py` y el bloque final de `bootstrap.py` (no los usaba nadie: escaneaba
  `/dev/input` al importar y lo tiraba). `applications.py` solo ignora `GLib.Error` al recordar la
  aplicación. Quedan los de `transfers.py` (deshace y relanza) y el de la CLI de `applications.py`
  (informa y sale con 1), que son correctos.

- [x] **Diálogos sin botón de cerrar** (2026-11-08, sin commit). `Desktop.add_close_header` pone la
  cabecera de las ventanas propias (`WindowHeader`: título, ampliar, cerrar) a los diálogos que no
  la tienen; Esc ya cerraba (QDialog). Avisos (QMessageBox) e Inicio/Alt+Tab quedan como estaban.

- [x] **Mover** (`Vault.move`) no actualizaba los enlaces relativos (2026-11-08, sin commit). Ahora
  reescribe los que apuntan a lo movido y los que salen de las notas movidas
  (`rename_markdown_links` con `new_note_dir`). `tests/test_model.py`.

- [x] **Inicio (Super) no responde con la Papelera abierta detrás** (2026-11-08, sin commit).
  `dialog.exec()` hace el diálogo modal para toda la aplicación y bloqueaba Inicio. La Papelera
  y los demás diálogos que no esperan respuesta se abren con `show_dialog` (`shell.py`), sin bloquear.

- [x] Tres escritorios duplicados en pantalla → uno solo (rama `arreglo-escritorios-duplicados`,
  sin commit todavía).
