# SPDX-License-Identifier: GPL-3.0-only
"""Programas recomendados del instalador, por categorías.

Cada entrada: nombre, descripción corta, origen ('flathub' o 'system') e id (id de Flathub o
paquetes del sistema separados por espacios; un dict {'arch': …, 'fedora': …} si los nombres
cambian). 'after' son servicios que hay que activar después (solo paquetes del sistema)."""
from . import distro


def app(name, summary, source, id, after=()):
    return {'name': name, 'summary': summary, 'source': source, 'id': id, 'after': tuple(after)}


CATALOG = (
    ('Utilidades', (
        app('Input Remapper', 'Reasigna teclas y botones de teclados, ratones y mandos', 'system', 'input-remapper',
            ['input-remapper']),
        app('Piper', 'Configura ratones gaming: DPI, botones y luces', 'system',
            {'arch': 'piper libratbag', 'fedora': 'piper libratbag-ratbagd'}, ['ratbagd']),
        app('Solaar', 'Dispositivos Logitech: batería, emparejado y botones', 'system', 'solaar'),
        app('OpenRGB', 'Controla la iluminación RGB de todo el equipo', 'flathub', 'org.openrgb.OpenRGB'),
        app('Mission Center', 'Monitor del sistema: CPU, memoria, discos y GPU', 'flathub', 'io.missioncenter.MissionCenter'),
        app('Easy Effects', 'Ecualizador y efectos para el sonido del sistema', 'flathub', 'com.github.wwmm.easyeffects'),
        app('pwvucontrol', 'Volumen por aplicación y dispositivo (PipeWire)', 'flathub', 'com.saivert.pwvucontrol'),
        app('LocalSend', 'Pasa archivos al móvil y a otros equipos sin cables', 'flathub', 'org.localsend.localsend_app'),
        app('Input Leap', 'Un teclado y un ratón para varios ordenadores', 'flathub', 'io.github.input_leap.input-leap'),
        app('RustDesk', 'Escritorio remoto', 'flathub', 'com.rustdesk.RustDesk'),
        app('KeePassXC', 'Gestor de contraseñas sin nube', 'flathub', 'org.keepassxc.KeePassXC'),
        app('SyncThingy', 'Syncthing: sincroniza carpetas entre equipos', 'flathub', 'com.github.zocker_160.SyncThingy'),
        app('Pika Backup', 'Copias de seguridad sencillas', 'flathub', 'org.gnome.World.PikaBackup'),
        app('PDF Arranger', 'Une, separa y reordena páginas de PDF', 'flathub', 'com.github.jeromerobert.pdfarranger'),
        app('qBittorrent', 'Cliente de torrents', 'flathub', 'org.qbittorrent.qBittorrent'),
        app('Gear Lever', 'Integra y actualiza AppImages', 'flathub', 'it.mijorus.gearlever'),
        app('Flatseal', 'Permisos de las aplicaciones de Flathub', 'flathub', 'com.github.tchx84.Flatseal'),
        app('Warehouse', 'Gestiona y limpia las aplicaciones de Flathub', 'flathub', 'io.github.flattool.Warehouse'),
    )),
    ('Multimedia', (
        app('Jellyfin', 'Tu servidor Jellyfin: pelis, series y música', 'flathub', 'org.jellyfin.JellyfinDesktop'),
        app('VLC', 'Reproduce cualquier vídeo o audio', 'flathub', 'org.videolan.VLC'),
        app('mpv', 'Reproductor de vídeo ligero', 'flathub', 'io.mpv.Mpv'),
        app('Spotify', 'Música en streaming', 'flathub', 'com.spotify.Client'),
        app('OBS Studio', 'Graba y emite la pantalla', 'flathub', 'com.obsproject.Studio'),
        app('Kdenlive', 'Editor de vídeo', 'flathub', 'org.kde.kdenlive'),
        app('Audacity', 'Editor de audio', 'flathub', 'org.audacityteam.Audacity'),
        app('Krita', 'Pintura digital', 'flathub', 'org.kde.krita'),
        app('Inkscape', 'Dibujo vectorial', 'flathub', 'org.inkscape.Inkscape'),
    )),
    ('Ingeniería y programación', (
        app('VSCodium', 'Editor de código (VS Code sin telemetría)', 'flathub', 'com.vscodium.codium'),
        app('FreeCAD', 'CAD 3D paramétrico', 'flathub', 'org.freecad.FreeCAD'),
        app('KiCad', 'Esquemas y placas de circuito', 'flathub', 'org.kicad.KiCad'),
        app('OpenSCAD', 'CAD 3D escrito como código', 'flathub', 'org.openscad.OpenSCAD'),
        app('PrusaSlicer', 'Laminador para impresión 3D', 'flathub', 'com.prusa3d.PrusaSlicer'),
        app('Blender', 'Modelado, animación y render 3D', 'flathub', 'org.blender.Blender'),
        app('GNU Octave', 'Cálculo numérico compatible con MATLAB', 'flathub', 'org.octave.Octave'),
        app('GNOME Boxes', 'Máquinas virtuales', 'flathub', 'org.gnome.Boxes'),
    )),
    ('Juegos', (
        app('Steam', 'Tienda y biblioteca de juegos', 'flathub', 'com.valvesoftware.Steam'),
        app('Heroic', 'Juegos de Epic, GOG y Amazon', 'flathub', 'com.heroicgameslauncher.hgl'),
        app('Lutris', 'Organiza juegos de cualquier origen', 'flathub', 'net.lutris.Lutris'),
        app('ProtonUp-Qt', 'Instala versiones de Proton y Wine-GE', 'flathub', 'net.davidotek.pupgui2'),
        app('Bottles', 'Programas de Windows con Wine', 'flathub', 'com.usebottles.bottles'),
        app('Prism Launcher', 'Minecraft con varias instancias y mods', 'flathub', 'org.prismlauncher.PrismLauncher'),
        app('Moonlight', 'Juega en streaming desde tu PC', 'flathub', 'com.moonlight_stream.Moonlight'),
    )),
    ('Internet y notas', (
        app('Firefox', 'Navegador web', 'flathub', 'org.mozilla.firefox'),
        app('Zen Browser', 'Navegador basado en Firefox', 'flathub', 'app.zen_browser.zen'),
        app('Signal', 'Mensajería cifrada', 'flathub', 'org.signal.Signal'),
        app('Telegram', 'Mensajería', 'flathub', 'org.telegram.desktop'),
        app('Vesktop', 'Discord, más ligero y sin rastreo', 'flathub', 'dev.vencord.Vesktop'),
        app('Obsidian', 'Notas en Markdown enlazadas', 'flathub', 'md.obsidian.Obsidian'),
        app('Anki', 'Tarjetas de memoria para estudiar', 'flathub', 'net.ankiweb.Anki'),
        app('Okular', 'Lector de PDF con anotaciones', 'flathub', 'org.kde.okular'),
    )),
)


def recommended():
    """Lista plana de entradas, cada una con su 'category'."""
    return [dict(entry, category=category) for category, entries in CATALOG for entry in entries]


def package_ids(entry, system=None):
    """Paquetes de la entrada en este sistema, separados por espacios."""
    ids = entry['id']
    return ids[(system or distro.current()).key] if isinstance(ids, dict) else ids


def is_installed(entry, flatpaks, packages, system=None):
    """¿Ya está? Flathub: por id de aplicación; sistema: todos sus paquetes."""
    if entry['source'] == 'flathub':
        return entry['id'] in flatpaks
    return all(name in packages for name in package_ids(entry, system).split())
