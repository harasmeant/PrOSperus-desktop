# Receta experimental de imagen

Estos archivos describen una imagen de desarrollo con Fedora, Cage y la sesión
PrOSperus. La aplicación `0.3.2-dev` y su paquete Fedora están comprobados.
La nueva receta [ISO Live](../docs/ISO-LIVE.md) ya genera una imagen con sus
dependencias incluidas y se ha comprobado su arranque UEFI, sesión gráfica,
creación de proyecto, guardado y búsqueda de notas en QEMU con 2 GiB. No es una distribución para uso diario.

La receta de arranque actual incluye `selinux=0`; no proporciona una política
SELinux adaptada al nuevo escritorio. La cuenta `prosperus` y su sesión local
pueden solicitar apagar/reiniciar la VM. No se deben trasladar esas decisiones
de desarrollo a una instalación de uso habitual sin revisarlas.

La receta anterior de ejecución con QEMU usa un disco con snapshot temporal, 2 vCPU,
2 GiB de RAM, sin tarjeta de red y VNC publicado únicamente en localhost.
Los scripts de construcción escriben archivos bajo `out/`; no requieren
instalar esta imagen en el disco del anfitrión.

Para probar la aplicación publicada, sigue `docs/FEDORA-DEMO.md` desde la raíz
del repositorio. `scripts/build-iso.sh` construye la ISO y `scripts/run-iso.sh`
la prueba mediante UEFI y unidad óptica, sin inyectar el kernel desde QEMU.
