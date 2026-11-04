# SPDX-License-Identifier: GPL-3.0-only
"""Sistema base sobre el que corre PrOSperus (Arch o Fedora): gestor de paquetes y nombres.

Todo lo que cambia entre distribuciones está aquí; el resto del escritorio no las distingue."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Distro:
    key: str            # 'arch' | 'fedora'
    label: str          # nombre visible: «Arch», «Fedora»
    package_suffixes: tuple  # archivos locales que sabe instalar

    def search_command(self, term):
        if self.key == 'arch':
            # Base de datos local: no hace falta red para buscar.
            return ['pacman', '-Ss', term]
        return ['dnf5', '-q', '-C', 'repoquery', '--available', '--latest-limit=1',
                '--queryformat=%{name}\t%{summary}\n', f'*{term}*']

    def parse_search(self, output):
        """[{'source': 'system', 'id', 'name', 'summary'}] sin repetir nombres."""
        found, seen = [], set()
        if self.key == 'arch':
            # «extra/nombre versión [instalado]» y debajo la descripción con sangría.
            pairs, current = [], None
            for line in output.splitlines():
                if line[:1].isspace():
                    if current:
                        pairs.append((current, line.strip())); current = None
                elif '/' in line:
                    current = line.split()[0].split('/', 1)[1]
            if current:
                pairs.append((current, ''))
        else:
            pairs = [(n.strip(), s.strip()) for n, _, s in (l.partition('\t') for l in output.splitlines())]
        for name, summary in pairs:
            if name and name not in seen:
                seen.add(name)
                found.append({'source': 'system', 'id': name, 'name': name, 'summary': summary})
        return found

    def install_command(self, packages):
        # shortcut: sudo -n usa el sudo sin contraseña de la imagen de desarrollo; usar pkexec en la de uso diario.
        if self.key == 'arch':
            # Arch no admite actualizaciones parciales: -Syu actualiza a la vez que instala.
            return ['sudo', '-n', 'pacman', '-Syu', '--noconfirm', '--needed', *packages]
        return ['sudo', '-n', 'dnf5', 'install', '-y', *packages]

    def install_file_command(self, path):
        if self.key == 'arch':
            return ['sudo', '-n', 'pacman', '-U', '--noconfirm', path]
        return ['sudo', '-n', 'dnf5', 'install', '-y', path]

    def installed_command(self):
        if self.key == 'arch':
            return ['pacman', '-Qq']
        return ['rpm', '-qa', '--queryformat', '%{NAME}\n']

    def shell_install(self, packages):
        """Orden de instalación escrita para mostrarla en una terminal o un mensaje."""
        if self.key == 'arch':
            return 'sudo pacman -Syu --needed ' + packages
        return 'sudo dnf install -y ' + packages


ARCH = Distro('arch', 'Arch', ('.pkg.tar.zst', '.pkg.tar.xz'))
FEDORA = Distro('fedora', 'Fedora', ('.rpm',))


def detect(os_release=Path('/etc/os-release')):
    """Arch (o derivada) si /etc/os-release lo dice; si no, Fedora, como hasta ahora."""
    try:
        fields = dict(line.split('=', 1) for line in os_release.read_text().splitlines() if '=' in line)
    except OSError:
        return FEDORA
    ids = (fields.get('ID', '') + ' ' + fields.get('ID_LIKE', '')).replace('"', '').split()
    return ARCH if 'arch' in ids else FEDORA


@lru_cache(maxsize=1)
def current():
    return detect()
