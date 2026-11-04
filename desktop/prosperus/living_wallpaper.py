# SPDX-License-Identifier: GPL-3.0-only
"""Fondo animado (opcional): la tela del fondo ondula muy despacio, dibujada por la GPU.

Es una capa OpenGL debajo de las tarjetas del mapa: cada fotograma solo lo pinta la GPU (un shader que
desplaza un poco la imagen donde hay dibujo y deja quieto lo oscuro, donde va el texto); las tarjetas y
las ramas no se vuelven a dibujar. También hace el fundido de los fondos por horas y el velo oscuro.
Apagado por defecto: en equipos sin GPU sería un gasto continuo."""
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram, QOpenGLTexture
from PySide6.QtOpenGLWidgets import QOpenGLWidget

FPS = 30
GL_TRIANGLE_STRIP, GL_FLOAT, GL_COLOR_BUFFER_BIT = 0x0005, 0x1406, 0x00004000

VERTEX = '''
attribute vec2 position;
varying vec2 uv;
void main() {
    uv = position * 0.5 + 0.5;
    gl_Position = vec4(position, 0.0, 1.0);
}
'''

# Ondulación: dos ondas lentas cruzadas, solo donde la imagen tiene luz o color (telas, hojas);
# un brillo que se desplaza con la onda da la sensación de tela. Luego el fundido y el velo.
FRAGMENT = '''
uniform sampler2D before;
uniform sampler2D after;
uniform vec4 crop_before;
uniform vec4 crop_after;
uniform float blend;
uniform float t;
uniform float strength;
uniform vec4 base;
uniform vec4 tint;
uniform vec3 veil;
uniform float has_before;
uniform float has_after;
varying vec2 uv;

vec4 fabric(sampler2D image, vec4 crop, vec2 p) {
    vec2 at = crop.xy + vec2(p.x, 1.0 - p.y) * crop.zw;
    vec4 still = texture2D(image, at);
    float lit = max(still.r, max(still.g, still.b));
    float mask = smoothstep(0.10, 0.34, lit) * strength;
    vec2 wave = vec2(sin(p.y * 7.0 + t * 0.50 + sin(p.x * 3.0 + t * 0.21) * 1.6),
                     cos(p.x * 6.0 - t * 0.37 + p.y * 2.5)) * 0.0032;
    vec4 moved = texture2D(image, at + wave * mask * crop.zw);
    float sheen = 1.0 + 0.045 * mask * sin(p.x * 5.0 + p.y * 4.0 - t * 0.6);
    return vec4(mix(still.rgb, moved.rgb, mask) * sheen, 1.0);
}

void main() {
    vec4 colour = base;
    if (has_before > 0.5) colour = fabric(before, crop_before, uv);
    if (has_after > 0.5) colour = mix(colour, fabric(after, crop_after, uv), blend);
    float y = 1.0 - uv.y;
    float alpha = y < 0.22 ? mix(veil.x, veil.y, y / 0.22)
                : y < 0.70 ? veil.y
                : mix(veil.y, veil.z, (y - 0.70) / 0.30);
    gl_FragColor = vec4(mix(colour.rgb, tint.rgb, alpha), 1.0);
}
'''


def cover_crop(image_size, target_size):
    """Parte de la imagen que se ve al llenar la pantalla sin deformarla (x, y, ancho, alto en 0-1)."""
    iw, ih = image_size
    tw, th = target_size
    if not iw or not ih or not tw or not th:
        return (0.0, 0.0, 1.0, 1.0)
    scale = max(tw / iw, th / ih)
    fw, fh = min(1.0, tw / scale / iw), min(1.0, th / scale / ih)
    return ((1 - fw) / 2, (1 - fh) / 2, fw, fh)


class LivingWallpaper(QOpenGLWidget):
    """Capa del fondo con movimiento. set_scene() le da imágenes, mezcla y colores, como a Wallpaper."""

    def __init__(self, parent=None, strength=1.0):
        super().__init__(parent)
        self.strength = strength
        self.paths = (None, None)
        self.images = {}
        self.textures = {}
        self.mix = 1.0
        self.base, self.tint, self.shade = QColor('#101010'), QColor('#000000'), (110, 30, 120)
        self.program = self.buffer = None
        self.started = time.monotonic()
        self.timer = QTimer(self); self.timer.setInterval(round(1000 / FPS)); self.timer.timeout.connect(self.update)

    def set_scene(self, previous, current, mix, base, tint, shade=(110, 30, 120)):
        previous = None if previous == current else previous
        self.paths = (previous, current)
        self.mix = mix if previous else 1.0
        self.base, self.tint = QColor(base), QColor(tint)
        self.shade = shade if isinstance(shade, tuple) else (shade, shade, shade)
        for path in self.paths:
            if path and path not in self.images:
                image = QImage(str(path))
                self.images[path] = None if image.isNull() else image.convertToFormat(QImage.Format.Format_RGBA8888)
        # Solo se guardan las dos imágenes en uso: la memoria no crece al cambiar de proyecto.
        for path in [p for p in self.images if p not in self.paths]:
            self.images.pop(path)
            texture = self.textures.pop(path, None)
            if texture is not None and self.context() is not None:
                self.makeCurrent(); texture.destroy(); self.doneCurrent()
        self.update()

    def showEvent(self, event):
        super().showEvent(event); self.timer.start()

    def hideEvent(self, event):
        # Oculto (otra pantalla, minimizado) no gasta nada.
        self.timer.stop(); super().hideEvent(event)

    def initializeGL(self):
        self.program = QOpenGLShaderProgram(self)
        ok = (self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX)
              and self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT))
        self.program.bindAttributeLocation('position', 0)
        if not ok or not self.program.link():
            self.program = None
            return
        import struct
        quad = struct.pack('8f', -1, -1, 1, -1, -1, 1, 1, 1)
        self.buffer = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer); self.buffer.create(); self.buffer.bind()
        self.buffer.allocate(quad, len(quad)); self.buffer.release()

    def texture(self, path):
        if path not in self.textures and self.images.get(path) is not None:
            texture = QOpenGLTexture(self.images[path], QOpenGLTexture.MipMapGeneration.DontGenerateMipMaps)
            texture.setMinMagFilters(QOpenGLTexture.Filter.Linear, QOpenGLTexture.Filter.Linear)
            texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
            self.textures[path] = texture
        return self.textures.get(path)

    def paintGL(self):
        gl = self.context().functions()
        if self.program is None:
            gl.glClearColor(self.base.redF(), self.base.greenF(), self.base.blueF(), 1.0)
            gl.glClear(GL_COLOR_BUFFER_BIT)
            return
        ratio = self.devicePixelRatioF()
        size = (self.width() * ratio, self.height() * ratio)
        self.program.bind()
        for unit, (name, path) in enumerate((('before', self.paths[0]), ('after', self.paths[1]))):
            texture = self.texture(path) if path else None
            flag = 'has_' + name
            self.program.setUniformValue1f(flag, 1.0 if texture is not None else 0.0)
            if texture is not None:
                texture.bind(unit)
                self.program.setUniformValue1i(name, unit)
                image = self.images[path]
                self.program.setUniformValue('crop_' + name, *cover_crop((image.width(), image.height()), size))
        self.program.setUniformValue1f('blend', float(self.mix))
        self.program.setUniformValue1f('t', float(time.monotonic() - self.started))
        self.program.setUniformValue1f('strength', float(self.strength))
        self.program.setUniformValue('base', self.base.redF(), self.base.greenF(), self.base.blueF(), 1.0)
        self.program.setUniformValue('tint', self.tint.redF(), self.tint.greenF(), self.tint.blueF(), 1.0)
        self.program.setUniformValue('veil', *(alpha / 255 for alpha in self.shade))
        self.buffer.bind()
        self.program.enableAttributeArray(0)
        self.program.setAttributeBuffer(0, GL_FLOAT, 0, 2)
        gl.glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        self.program.disableAttributeArray(0)
        self.buffer.release()
        for unit, path in enumerate(self.paths):
            if path and path in self.textures:
                self.textures[path].release(unit)
        self.program.release()
