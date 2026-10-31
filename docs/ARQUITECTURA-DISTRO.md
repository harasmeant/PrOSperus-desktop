# Componentes de distro y estado PrOSperus · arquitectura y diseño

## Componentes necesarios para una distro funcional
1. **Boot / Firmware:** UEFI (OVMF) + bootloader (UKI/systemd-boot/GRUB) ✅ parcial
2. **Kernel / Módulos:** kernel-core, dracut, drivers virtio + reales ❌ faltan drivers GPU/WiFi/SD
3. **Init:** systemd + pam (systemd-pam corregido) ✅
4. **Sesión gráfica:** Cage (compositor) + greetd + Qt/Wayland ✅ básico
5. **Escritorio / UI:** PrOSperus (Python/Qt) ✅ independiente
6. **Gestión de archivos / proyectos:** GIO, explorador, mapa radial ✅
7. **Aplicaciones:** buscar/crear notas, favoritos globales ✅ básico
8. **Red:** NetworkManager / wpa_supplicant ❌ no incluido en imagen
9. **Persistencia:** disco ext4 + fstab + instalador ❌ no hay
10. **Instalador:** Calamares / script personalizado ❌ no hay
11. **Herramientas de sistema:** audio (pipewire/alsa), brillo, volumén, teclado multimedia ❌ parcial (wpctl/playerctl/brightnessctl en desktop)
12. **Seguridad / usuarios:** root bloqueado, usuario `prosperus` (uid 1000), polkit para VM ✅
13. **Documentación / evidencia:** ISO-LIVE.md, VM-MINIMOS.md, validación ✅ parcial

## Qué tenemos hoy
- Imagen `prosperus.qcow2` que arranca UEFI (`BOOTX64.EFI` via UKI)
- `systemd-pam` corregido → `greetd` arranca la sesión
- `Containerfile.base` con Mesa, Qt, Cage, GIO, polkit, kbd, font
- `build-image.sh` genera imagen cargable en Boxes
- `run-vm.sh` y `run-iso.sh` para QEMU
- Prototipo funcional: proyectos, notas, búsqueda por contenido, mapa radial, tarjetero

## Qué falta (prioridad)
**Crítico para uso real:**
- [ ] Instalar apps referenciadas: VSCodium (protocolo de escritorio), navegador, libreoffice, gimp (según demo-system/)
- [ ] Selector resolución + escala en la UI (Problema avanzado: `layout_settings.py` divide pantalla por defecto; falta `appearance.py` o settings)
- [ ] Captura y manejo de ratón en VM (probablemente `virtio-mouse` o evento Qt)
- [ ] Red funcional (`networkmanager` + `wireless-tools` en `Containerfile.base`)
- [ ] Persistencia: `fstab` generado por instalador o por imagen instalada; `machine-id` único por instalación
- [ ] Instalador mínimo (script o Calamares) para escribir a disco real

## Recomendaciones inmediatamente aplicables (diseño del proyecto)
- **Mantener Python/Qt independiente** (no atar a Obsidian ni a un DE específico)
- **Compositor `Cage`** (Wayland) sobre `greetd` (madrugador simple, no GNOME)
- **Base Fedora fija por digest**, paquetes de repos: permite actualizar sin romper la receta
- **Separar `image/` (construcción) de `desktop/` (aplicación) de `demo-system/` (datos)**
- **Uso de GIO** para lanzar apps externas (no shell commands) → seguridad
- **Mapa de archivos como representación**, no grafo semántico (límite documentado; no cambiar ahora)
- **No sustituir Cage por Sway** en ISO publicada aún (documentado como experimental)

## Recomendaciones inmediatas para que funcione en VM hoy
1. **UI:** Añadir a `desktop/prosperus/appearance.py` o `layout_settings.py` un selector de resolución (1360×850 / 900×650 / automático) y escala (1.0 / 1.25 / 1.5). Esto resuelve el "zoom" y la división.
2. **Ratón:** Verificar que `virtio-mouse` esté en `Containerfile.base` o que el evento de Qt capture el mouse en `desktop/prosperus/desktop_keys.py`
3. **Apps:** Añadir a `Containerfile.base` o `Containerfile`: `python3-pyside6` ya está; faltan `gimp`, `firefox`, `libreoffice-writer`, `vscodium` (o al menos los paquetes mínimos para que `launcher.py` los encuentre vía GIO). No instalar todo en imagen básica; usar repos en primera ejecución.
4. **Instalador:** Crear `scripts/install.sh` que parte `prosperus-uefi.raw` → escribe a `/dev/sda` → instala bootloader → crea usuario.
5. **Red:** Añadir `NetworkManager` y `wireless-tools`; configurar `systemd-networkd` como fallback.
6. **Persistencia:** En `image/Containerfile.live` asegurar que `dracut-live` permita overlay temporal; al instalar, quitar `rd.live.ram` y usar disco directo.
