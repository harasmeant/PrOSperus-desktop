# Receta experimental de imagen

Estos archivos describen una imagen de desarrollo con Fedora, Cage y la sesión
PrOSperus. La entrega `0.2.0-dev` que se ha comprobado es la aplicación y su
paquete para Fedora Live; **esta imagen no se ha reconstruido ni validado con
esa versión**. No es una distribución preparada para uso diario.

La receta de arranque actual incluye `selinux=0`; no proporciona una política
SELinux adaptada al nuevo escritorio. La cuenta `prosperus` y su sesión local
pueden solicitar apagar/reiniciar la VM. No se deben trasladar esas decisiones
de desarrollo a una instalación de uso habitual sin revisarlas.

La receta de ejecución con QEMU usa un disco con snapshot temporal, 2 vCPU,
2 GiB de RAM, sin tarjeta de red y VNC publicado únicamente en localhost.
Los scripts de construcción escriben archivos bajo `out/`; no requieren
instalar esta imagen en el disco del anfitrión.

Para probar la aplicación actual, sigue `docs/FEDORA-DEMO.md` desde la raíz
del repositorio. La construcción de una imagen se mantiene como trabajo
separado y pendiente de verificación.
