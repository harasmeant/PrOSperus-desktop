# SPDX-License-Identifier: GPL-3.0-only
"""Salvapantallas: los fondos de los proyectos en bucle, con zoom lento, fundidos y luces que flotan.

swayidle lo abre al rato sin usar el equipo (prosperus-salvapantallas). Baja el brillo de la pantalla,
silencia las notificaciones y bloquea los atajos de Sway (modo «salvapantallas») mientras se ve.
Al tocar el teclado o el ratón vuelve el escritorio; si ha pasado el tiempo de bloqueo, antes se
bloquea con swaylock, como hacían los salvapantallas de siempre.

Cada fotograma lo dibuja la GPU con un shader: dos imágenes (la que se ve y la siguiente) se mueven
despacio (efecto Ken Burns) y se funden; encima, un barrido de luz y unas motas en el tono del proyecto.
Las imágenes se cargan en otro hilo para que el movimiento no dé tirones."""
import argparse
import hashlib
import json
import math
import os
import signal
import struct
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QDateTime, QLocale, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram, QOpenGLTexture
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication

from .living_wallpaper import VERTEX, cover_crop
from .theme_state import current_palette, state_dir
from .window_session import SAVER_ID

APP_ID = SAVER_ID
FPS = 30
SLIDE = 40.0          # segundos de cada fondo (sin contar el fundido)
FADE = 6.0            # segundos de fundido entre fondos
GRACE = 1.5           # al abrirse, se ignora la entrada (el último movimiento del ratón)
JITTER = 14           # píxeles que puede moverse el ratón sin despertar
FADE_IN = 2.0         # segundos que tarda el escritorio en disolverse en el salvapantallas
DIM = 0.40            # brillo de la pantalla mientras se ve (fracción del que había)
MIN_BRIGHTNESS = 5    # %; nunca a oscuras del todo
MAX_IMAGES = 40
MAX_SIDE = 2880       # las imágenes se reducen a esto: menos memoria de vídeo
SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.avif')
GL_TRIANGLE_STRIP, GL_FLOAT = 0x0005, 0x1406

FRAGMENT = '''
uniform sampler2D img_a;
uniform sampler2D img_b;
uniform vec4 crop_a;
uniform vec4 crop_b;
uniform vec3 move_a;
uniform vec3 move_b;
uniform float has_a;
uniform float has_b;
uniform float blend;
uniform float t;
uniform float dim;
uniform float aspect;
uniform vec4 base;
uniform vec4 glow;
varying vec2 uv;

float hash(float n) { return fract(sin(n) * 43758.5453123); }

// move = (zoom, desplazamiento x, desplazamiento y); el desplazamiento nunca saca la vista de la imagen.
vec3 slide(sampler2D image, vec4 crop, vec3 move, vec2 p) {
    vec2 q = vec2(p.x, 1.0 - p.y);
    // Un poco de tela: una onda muy lenta donde la imagen tiene luz.
    vec2 wave = vec2(sin(q.y * 6.0 + t * 0.35), cos(q.x * 5.0 - t * 0.28)) * 0.0022;
    vec2 at = 0.5 + (q - 0.5) / move.x + move.yz + wave;
    return texture2D(image, crop.xy + clamp(at, 0.0, 1.0) * crop.zw).rgb;
}

void main() {
    vec3 colour = base.rgb;
    if (has_a > 0.5) colour = slide(img_a, crop_a, move_a, uv);
    if (has_b > 0.5) colour = mix(colour, slide(img_b, crop_b, move_b, uv), blend);

    // Barrido de luz en diagonal, uno cada ~30 s.
    float d = dot(uv, normalize(vec2(1.0, 0.55)));
    float sweep = exp(-pow((d - (fract(t / 30.0) * 2.6 - 0.6)) * 3.2, 2.0));
    colour += glow.rgb * sweep * 0.07;

    // Motas de luz desenfocadas que suben despacio.
    vec2 p = vec2(uv.x * aspect, uv.y);
    float motes = 0.0;
    for (int i = 0; i < 18; i++) {
        float f = float(i);
        float speed = 0.012 + hash(f * 3.1) * 0.02;
        vec2 c = vec2(hash(f * 7.7) * aspect + sin(t * 0.07 + f) * 0.06,
                      fract(hash(f * 1.3) + t * speed) * 1.3 - 0.15);
        float r = 0.012 + hash(f * 5.9) * 0.045;
        float twinkle = 0.55 + 0.45 * sin(t * (0.3 + hash(f) * 0.5) + f * 2.0);
        motes += smoothstep(r, r * 0.15, length(p - c)) * twinkle * (0.25 + hash(f * 9.1) * 0.5);
    }
    colour += mix(glow.rgb, vec3(1.0), 0.35) * motes * 0.16;

    // Viñeta suave y brillo bajo.
    float vignette = smoothstep(1.15, 0.35, length((uv - 0.5) * vec2(aspect, 1.0) * 0.9));
    colour *= mix(0.55, 1.0, vignette) * dim;
    gl_FragColor = vec4(colour, 1.0);
}
'''


def find_wallpapers(current, root=None, limit=MAX_IMAGES):
    """El fondo actual primero y después los de los demás proyectos (wallpaper.* y los de cada hora),
    sin carpetas ocultas ni enlaces, hasta `limit`. root: carpeta de los proyectos."""
    current = Path(current) if current else None
    if root is None:
        projects = Path.home() / 'Proyectos'
        if current and projects in current.parents:
            root = projects
        else:
            root = current.parent if current else projects
    found = [current] if current and current.is_file() else []
    root = Path(root)
    if root.is_dir():
        for folder, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__'))
            if len(Path(folder).relative_to(root).parts) >= 3:
                dirs[:] = []
            for name in sorted(files):
                path = Path(folder) / name
                if (path.suffix.lower() in SUFFIXES and (path.stem == 'wallpaper' or path.stem.startswith('wallpaper-'))
                        and not path.is_symlink() and path not in found):
                    found.append(path)
            if len(found) >= limit:
                break
    return found[:limit]


def motion(index, progress):
    """Zoom y desplazamiento del fondo `index` en el momento `progress` (0-1) de su vida.
    Cada fondo tiene su dirección (fija, para que el bucle sea siempre igual)."""
    seed = hashlib.blake2b(str(index).encode(), digest_size=4).digest()
    zoom_in = seed[0] % 2 == 0
    angle = seed[1] / 255 * 2 * math.pi
    eased = 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, progress)))
    zoom = 1.05 + 0.13 * (eased if zoom_in else 1 - eased)
    reach = (1 - 1 / zoom) / 2 * 0.9           # lo que se puede mover sin salirse de la imagen
    travel = (eased - 0.5) * 2 * reach
    return zoom, math.cos(angle) * travel, math.sin(angle) * travel


def timeline(elapsed, slide=SLIDE, fade=FADE):
    """(fondo actual, siguiente, mezcla, avance del actual, avance del siguiente) a los `elapsed` s."""
    k = int(elapsed // slide)
    local = elapsed - k * slide
    start = slide - fade
    mix = 0.0 if local < start else (local - start) / fade
    mix = mix * mix * (3 - 2 * mix)
    life = slide + fade                       # cada fondo se mueve desde que empieza a fundirse
    return k, k + 1, mix, (local + fade) / life, max(0.0, local - start) / life


def load_image(path, width, height):
    """Imagen lista para textura, reducida a lo que hace falta para cubrir la pantalla con zoom."""
    image = QImage(str(path))
    if image.isNull():
        return None
    target = max(width, height) * 1.25
    longest = max(image.width(), image.height())
    if longest > min(MAX_SIDE, target):
        image = image.scaled(round(image.width() * min(MAX_SIDE, target) / longest),
                             round(image.height() * min(MAX_SIDE, target) / longest),
                             Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    return image.convertToFormat(QImage.Format.Format_RGBA8888)


class Saver(QOpenGLWidget):
    """Una ventana a pantalla completa por monitor; `offset` hace que cada uno empiece en otro fondo."""

    def __init__(self, session, screen, offset):
        super().__init__()
        self.session, self.offset = session, offset
        self.program = self.buffer = None
        self.textures = {}
        self.setScreen(screen)
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.setMouseTracking(True)
        # Título con el nombre de la salida: Sway la lleva a su pantalla (Session.place).
        self.output = screen.name()
        self.setWindowTitle(f'Salvapantallas {self.output}')
        self.start_pos = None
        self.timer = QTimer(self); self.timer.setInterval(round(1000 / FPS)); self.timer.timeout.connect(self.update)
        self.timer.start()

    def image_path(self, k):
        paths = self.session.paths
        return paths[(k + self.offset) % len(paths)] if paths else None

    # --- Entrada: cualquier tecla, clic o movimiento claro despierta.
    def keyPressEvent(self, event): self.session.wake()
    def mousePressEvent(self, event): self.session.wake()
    def wheelEvent(self, event): self.session.wake()

    def mouseMoveEvent(self, event):
        pos = event.globalPosition()
        if self.start_pos is None or not self.session.awake_for_input():
            self.start_pos = pos
        elif (pos - self.start_pos).manhattanLength() > JITTER:
            self.session.wake()

    # --- Dibujo
    def initializeGL(self):
        self.program = QOpenGLShaderProgram(self)
        ok = (self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX)
              and self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT))
        self.program.bindAttributeLocation('position', 0)
        if not ok or not self.program.link():
            print('salvapantallas: el shader no compila', self.program.log(), file=sys.stderr)
            self.program = None
            return
        self.context().aboutToBeDestroyed.connect(self.release_textures)
        quad = struct.pack('8f', -1, -1, 1, -1, -1, 1, 1, 1)
        self.buffer = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer); self.buffer.create(); self.buffer.bind()
        self.buffer.allocate(quad, len(quad)); self.buffer.release()

    def release_textures(self):
        self.makeCurrent()
        for texture in self.textures.values():
            texture.destroy()
        self.textures.clear()
        self.doneCurrent()

    def texture(self, path):
        if path is None:
            return None, None
        image = self.session.image(path, self.width() * self.devicePixelRatioF(),
                                   self.height() * self.devicePixelRatioF())
        if image is None:
            return None, None
        if path not in self.textures:
            texture = QOpenGLTexture(image, QOpenGLTexture.MipMapGeneration.DontGenerateMipMaps)
            texture.setMinMagFilters(QOpenGLTexture.Filter.Linear, QOpenGLTexture.Filter.Linear)
            texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
            self.textures[path] = texture
        return self.textures[path], image

    def paintGL(self):
        session = self.session
        elapsed = time.monotonic() - session.started
        a, b, mix, progress_a, progress_b = timeline(elapsed + self.offset * 7.0)
        ratio = self.devicePixelRatioF()
        size = (self.width() * ratio, self.height() * ratio)
        gl = self.context().functions()
        base = session.colors_base
        if self.program is None:
            gl.glClearColor(base.redF() * 0.4, base.greenF() * 0.4, base.blueF() * 0.4, 1.0)
            gl.glClear(0x00004000)
        else:
            paths = (self.image_path(a), self.image_path(b))
            session.prefetch([self.image_path(k) for k in (a, b, b + 1)], *size)
            self.program.bind()
            for unit, (name, path, k, progress) in enumerate((('a', paths[0], a, progress_a),
                                                               ('b', paths[1], b, progress_b))):
                texture, image = self.texture(path)
                self.program.setUniformValue1f('has_' + name, 1.0 if texture is not None else 0.0)
                if texture is not None:
                    texture.bind(unit)
                    self.program.setUniformValue1i('img_' + name, unit)
                    self.program.setUniformValue('crop_' + name, *cover_crop((image.width(), image.height()), size))
                self.program.setUniformValue('move_' + name, *motion(k + self.offset, progress))
            self.program.setUniformValue1f('blend', float(mix if paths[1] is not None else 0.0))
            self.program.setUniformValue1f('t', float(elapsed))
            self.program.setUniformValue1f('dim', float(session.dim))
            self.program.setUniformValue1f('aspect', float(size[0] / max(1.0, size[1])))
            self.program.setUniformValue('base', base.redF(), base.greenF(), base.blueF(), 1.0)
            glow = session.colors_glow
            self.program.setUniformValue('glow', glow.redF(), glow.greenF(), glow.blueF(), 1.0)
            self.buffer.bind()
            self.program.enableAttributeArray(0)
            self.program.setAttributeBuffer(0, GL_FLOAT, 0, 2)
            gl.glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
            self.program.disableAttributeArray(0)
            self.buffer.release()
            for unit, path in enumerate(paths):
                if path in self.textures:
                    self.textures[path].release(unit)
            self.program.release()
            # Solo quedan en la GPU las dos imágenes en uso.
            for path in [p for p in self.textures if p not in paths]:
                self.textures.pop(path).destroy()
        self.paint_clock(elapsed)

    def paint_clock(self, elapsed):
        """Hora y fecha abajo a la izquierda, moviéndose muy despacio (para no marcar la pantalla)."""
        now = QDateTime.currentDateTime()
        locale = QLocale(QLocale.Language.Spanish, QLocale.Country.Spain)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        x = w * (0.07 + 0.05 * math.sin(elapsed / 97.0 + self.offset))
        y = h * (0.80 + 0.05 * math.sin(elapsed / 71.0 + self.offset * 2))
        fade = min(1.0, max(0.0, (elapsed - 0.5) / FADE_IN))
        text = QColor(self.session.colors_text); text.setAlphaF(0.88 * fade)
        shadow = QColor(0, 0, 0, round(110 * fade))
        big = QFont('DejaVu Sans', max(28, round(h / 11))); big.setWeight(QFont.Weight.Light)
        small = QFont('DejaVu Sans', max(11, round(h / 48)))
        date = locale.toString(now.date(), "dddd, d 'de' MMMM")
        for font, line, top in ((big, now.toString('HH:mm'), y - h / 9), (small, date[:1].upper() + date[1:], y + h / 60)):
            painter.setFont(font)
            rect = QRectF(x, top, w * 0.8, h / 7)
            painter.setPen(QPen(shadow)); painter.drawText(rect.translated(QPointF(0, 2)), Qt.AlignmentFlag.AlignLeft, line)
            painter.setPen(QPen(text)); painter.drawText(rect, Qt.AlignmentFlag.AlignLeft, line)
        painter.end()


def run(argv, **kwargs):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=5, check=False, **kwargs)
    except (OSError, subprocess.SubprocessError):
        return None


class Session:
    """Lo común a todas las pantallas: imágenes, colores, brillo, notificaciones, atajos y salida."""

    def __init__(self, app, lock_after):
        self.app, self.lock_after = app, lock_after
        self.started = time.monotonic()
        self.leaving = False
        directory = state_dir()
        colors = current_palette(directory)
        self.colors_base, self.colors_glow, self.colors_text = QColor(colors.base), QColor(colors.accent), QColor(colors.text)
        wallpaper = None
        try:
            wallpaper = json.loads((directory / 'theme.json').read_text(encoding='utf-8')).get('wallpaper') or None
        except (OSError, TypeError, ValueError, AttributeError):
            pass
        self.paths = find_wallpapers(wallpaper)
        self.images, self.pending = {}, {}
        self.loader = ThreadPoolExecutor(max_workers=1)
        self.dim = 1.0
        self.backlight = self.start_brightness = None
        self.muted_notifications = False

    def image(self, path, width, height):
        self.prefetch([path], width, height)
        future = self.pending.get(path)
        if future is not None and future.done():
            self.images[path] = future.result()
            del self.pending[path]
        return self.images.get(path)

    def prefetch(self, paths, width, height):
        wanted = {p for p in paths if p is not None}
        for path in wanted - self.images.keys() - self.pending.keys():
            self.pending[path] = self.loader.submit(load_image, path, width, height)
        # Memoria acotada: se suelta lo que ya no se va a ver pronto (con varias pantallas, algo más).
        keep = 3 * max(1, len(QGuiApplication.screens()))
        for path in list(self.images)[:-keep]:
            if path not in wanted:
                del self.images[path]

    def mark(self, on):
        """Marca de «No molestar» puesto por el salvapantallas: si se cuelga, el lanzador lo quita."""
        directory = state_dir()
        if directory is None:
            return
        try:
            marker = directory / 'salvapantallas.dnd'
            marker.touch() if on else marker.unlink(missing_ok=True)
        except OSError:
            pass

    def place(self, windows):
        """Con Wayland la ventana no elige pantalla: se lo pide a Sway, cada una a su salida."""
        for window in windows:
            run(['swaymsg', f'[app_id="{APP_ID}" title="^Salvapantallas {window.output}$"]',
                 'move', 'container', 'to', 'output', window.output])
        # Ya en su salida, la pantalla completa la pide Qt (así sabe su tamaño y no la deshace).
        QTimer.singleShot(150, lambda: [window.showFullScreen() for window in windows])

    def awake_for_input(self):
        return time.monotonic() - self.started > GRACE

    # --- Al entrar
    def begin(self):
        run(['swaymsg', 'mode', 'salvapantallas'])
        modes = run(['makoctl', 'mode'])
        if modes is not None and modes.returncode == 0 and 'do-not-disturb' not in modes.stdout.split():
            run(['makoctl', 'mode', '-a', 'do-not-disturb'])
            self.muted_notifications = True
            self.mark(True)
        info = run(['brightnessctl', '-m', '-c', 'backlight'])
        if info is not None and info.returncode == 0 and info.stdout.strip():
            try:
                self.start_brightness = int(info.stdout.split(',')[3].rstrip('%'))
            except (IndexError, ValueError):
                self.start_brightness = None
        if self.start_brightness is not None:
            run(['brightnessctl', '-q', '-c', 'backlight', '-s'])
            self.backlight = max(MIN_BRIGHTNESS, round(self.start_brightness * DIM))
        # Sin retroiluminación (monitor externo) el shader oscurece algo más.
        self.target_dim = 0.88 if self.backlight is not None else 0.6
        self.fade_step = 0
        self.fader = QTimer(); self.fader.setInterval(100); self.fader.timeout.connect(self.fade); self.fader.start()

    def fade(self):
        """Disuelve el escritorio en el salvapantallas y baja el brillo poco a poco."""
        steps = round(FADE_IN * 10)
        self.fade_step += 1
        f = min(1.0, self.fade_step / steps)
        run(['swaymsg', f'[app_id="{APP_ID}"]', 'opacity', f'{f:.2f}'])
        self.dim = 1.0 + (self.target_dim - 1.0) * f
        if self.backlight is not None and self.fade_step % 2 == 0:
            level = round(self.start_brightness + (self.backlight - self.start_brightness) * f)
            result = run(['brightnessctl', '-q', '-c', 'backlight', 'set', f'{level}%'])
            if result is None or result.returncode != 0:
                # Sin permiso sobre la retroiluminación: oscurece la imagen en su lugar.
                self.backlight = self.start_brightness = None
                self.target_dim = 0.6
        if f >= 1.0:
            self.fader.stop()

    # --- Al salir
    def wake(self):
        if self.leaving or not self.awake_for_input():
            return
        self.leaving = True
        if self.lock_after is not None and time.monotonic() - self.started >= self.lock_after:
            # prosperus-bloquear vuelve cuando swaylock ya tiene la pantalla: nunca se ve el escritorio.
            try:
                subprocess.run(['/usr/bin/prosperus-bloquear'], check=False, timeout=30)
            except (OSError, subprocess.SubprocessError):
                pass
        self.restore()
        self.app.quit()

    def restore(self):
        if getattr(self, 'fader', None) is not None:
            self.fader.stop()
        if self.start_brightness is not None:
            run(['brightnessctl', '-q', '-c', 'backlight', '-r'])
        if self.muted_notifications:
            run(['makoctl', 'mode', '-r', 'do-not-disturb'])
            self.muted_notifications = False
            self.mark(False)
        run(['swaymsg', 'mode', 'default'])
        self.loader.shutdown(wait=False, cancel_futures=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Salvapantallas de PrOSperus')
    parser.add_argument('--bloquear-tras', type=float, default=None, metavar='SEGUNDOS',
                        help='al volver, bloquea con swaylock si el salvapantallas lleva este tiempo')
    args = parser.parse_args(argv)
    QGuiApplication.setDesktopFileName(APP_ID)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv[:1])
    app.setApplicationName('Salvapantallas')
    session = Session(app, args.bloquear_tras)
    # Si lo cierran (swayidle, pkill), deja el brillo y los atajos como estaban.
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, lambda *_: (session.restore(), app.quit()))
    pulse = QTimer(); pulse.start(250); pulse.timeout.connect(lambda: None)  # deja a Python ver las señales
    windows = []
    for index, screen in enumerate(QGuiApplication.screens()):
        window = Saver(session, screen, index)
        window.show()
        windows.append(window)
    QTimer.singleShot(150, lambda: session.place(windows))
    session.begin()
    code = app.exec()
    return code


if __name__ == '__main__':
    sys.exit(main())
