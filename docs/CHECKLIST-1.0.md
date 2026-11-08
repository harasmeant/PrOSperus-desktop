# Checklist para la 1.0
<!-- SPDX-License-Identifier: GPL-3.0-only -->

**Definición de 1.0:** una persona puede instalar PrOSperus en su portátil, junto
a otro sistema o solo, y usarlo a diario **sin perder datos** y recibiendo
actualizaciones de seguridad.

**Base elegida: Debian 13 «trixie».** Arch y Fedora se congelan como
experimentales: no bloquean la 1.0 y no hace falta probarlas en cada versión.

Marca: `[x]` hecho · `[ ]` pendiente. Anotar fecha y equipo al marcar.

## 0. Bloqueantes de base

- [ ] **Núcleo actualizable.** Hoy está fijado con `apt-mark hold` porque el
      `prosperus.efi` instalado no se regenera solo. Hace falta un gancho
      (p. ej. en `/etc/kernel/postinst.d/`) que reconstruya el UKI al actualizar
      el núcleo, y quitar el `hold`. Sin esto no hay parches de seguridad del núcleo.
- [ ] **Actualizar PrOSperus sin reinstalar.** Decidir el mecanismo (paquete `.deb`
      propio en un repositorio apt, o similar) y probar 0.9 → 1.0 conservando `home/`.
- [x] **SwayFX compilado en la receta**: sustituido por `sway` de Debian (2026-11-07);
      SwayFX dejaba huecos sin repintar con AMD + NVIDIA.
- [ ] **Secure Boot:** firmar `prosperus.efi` (claves propias con `sbctl` o shim), o
      que el instalador avise claramente y explique cómo arrancar sin él.

## 1. Datos del usuario (lo que no se perdona)

- [x] Guardado atómico de notas (temporal + `fsync` + `os.replace`, en `model.py`).
      Falta la prueba manual de cortar la luz durante el guardado.
- [x] Borrar envía a `.papelera` con su origen y se recupera desde Crear › Papelera.
- [x] Renombrar actualiza wikilinks y enlaces Markdown relativos.
- [x] **Mover** actualiza los enlaces relativos como renombrar (2026-11-08, falta probar a mano).
- [ ] Una actualización y una reinstalación conservan `~/proyectos` y la configuración.
- [ ] El instalador a disco, probado en hardware real, no toca las demás particiones
      (ya lo comprueba en QEMU).

## 2. Funciones congeladas

Nada nuevo hasta la 1.0. Solo cerrar lo que hay en el [ROADMAP](ROADMAP.md):

- [x] Todos los diálogos propios tienen botón de cerrar (y Esc) (2026-11-08, falta probar a mano).
- [ ] Multipantalla: conectar y desconectar un monitor sin perder ventanas.
- [ ] Recuperar la disposición de ventanas tras reiniciar (o decidir dejarlo para 1.1).

## 3. Hardware real (Debian)

Completar la columna «Debian real» de [PRUEBAS-MINIMAS.md](PRUEBAS-MINIMAS.md)
en **al menos dos equipos distintos**: el portátil HP (híbrido NVIDIA) y uno
con gráfica solo integrada.

- [x] Portátil del autor: funciona (05-11-2026). Pasar el detalle a PRUEBAS-MINIMAS.
- [ ] Segundo equipo: portátil del trabajo, en dual boot (probablemente con Windows,
      BitLocker y Secure Boot: ver bloqueante de Secure Boot en la sección 0).

- [ ] Arranque UEFI, gráfica integrada, NVIDIA híbrida, monitor externo.
- [ ] Teclado español, panel táctil, Wi-Fi, cable, sonido, brillo, Bluetooth.
- [ ] Suspender y volver.
- [ ] Instalar un paquete con apt y uno de Flathub con red.
- [ ] Toda la sección «Escritorio» de PRUEBAS-MINIMAS.

## 4. Calidad del código

- [x] Tests en verde (05-11-2026: 226 pruebas). Los tests ya no leen los ajustes
      del usuario ni la versión de wob instalada.
- [ ] CI obligatoria en `main` (no fusionar en rojo).
- [ ] CI que construya o al menos valide la receta de Debian, no solo Fedora.
- [ ] Partir `desktop/prosperus/shell.py` (más de 2100 líneas) en módulos más pequeños.
- [x] Revisar los `except Exception` que ocultan errores (2026-11-08, ver BUGS.md).

## 5. Publicación

- [ ] Licencias de todo lo que entra en la ISO: sin sonidos ni fondos con derechos
      sin aclarar (hoy excluidos por `.gitignore`; comprobar que no entran en la
      imagen publicada). Inventario de fuentes, cursores e iconos con su licencia.
- [ ] README de la 1.0 con descarga directa de la ISO y su SHA-256.
- [ ] Separar `docs/` de usuario (instalar, usar, recuperar) de las notas de desarrollo.
- [ ] Fusionar o borrar ramas y worktrees viejos; `main` refleja lo publicado.
- [ ] Guía «si algo va mal»: arrancar el otro sistema, recuperar notas, desinstalar.

## 6. Versión candidata

- [ ] Publicar **1.0-rc1** (ISO Debian) como prerelease.
- [ ] 2 o 3 personas externas la usan una semana y reportan.
- [ ] Sin fallos que pierdan datos ni bloqueen el arranque → **1.0**.
