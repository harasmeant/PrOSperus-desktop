# SPDX-License-Identifier: GPL-3.0-only
"""Recolorea un fondo conservando su diseño: cada familia de tono del original pasa a un color nuevo,
manteniendo la luz y el sombreado de cada píxel."""
import colorsys, math
from PySide6.QtGui import QImage, QColor


def families(img, count=2):
    """Los tonos dominantes (grados), pesados por saturación y brillo; separados al menos 45°."""
    small = img.scaled(96, 60)
    bins = [0.0] * 36
    for y in range(small.height()):
        for x in range(small.width()):
            c = QColor(small.pixel(x, y)); h = c.hsvHueF()
            if h >= 0:
                bins[int(h * 36) % 36] += c.saturationF() * c.valueF()
    smooth = [bins[i - 1] * .5 + bins[i] + bins[(i + 1) % 36] * .5 for i in range(36)]
    peaks = []
    for i in sorted(range(36), key=lambda i: -smooth[i]):
        if all(min(abs(i - j), 36 - abs(i - j)) >= 5 for j in peaks):
            peaks.append(i)
        if len(peaks) == count:
            break
    return [p * 10 + 5 for p in peaks]


def recolour(img, targets, neutral=None):
    """targets: por cada familia (en el orden de families()) un dict con
    hue, sat (factor), light (función l→l), y neutral: igual para los píxeles casi grises (el fondo)."""
    img = img.convertToFormat(QImage.Format.Format_RGB32)
    peaks = families(img, len(targets))
    out = QImage(img.size(), QImage.Format.Format_RGB32)
    width, height = img.width(), img.height()
    cache = {}
    for y in range(height):
        for x in range(width):
            rgb = img.pixel(x, y) & 0xffffff
            key = rgb >> 1 & 0x7f7f7f  # agrupa colores casi iguales: 7 bits por canal
            hit = cache.get(key)
            if hit is None:
                r, g, b = (rgb >> 16) / 255, (rgb >> 8 & 255) / 255, (rgb & 255) / 255
                h, l, s = colorsys.rgb_to_hls(r, g, b)
                deg = h * 360
                # Reparto suave entre familias según la distancia de tono: sin saltos ni manchas.
                dist = [min(abs(deg - q), 360 - abs(deg - q)) for q in peaks]
                weights = [math.exp(-(d / 38) ** 2) + 1e-6 for d in dist]
                total = sum(weights)
                grey = max(0.0, min(1.0, (s * min(l, 1 - l) * 2 - .02) / .12))
                rr = gg = bb = 0.0
                for t, w in zip(targets, weights):
                    n = neutral or t
                    sat = s * t['sat'] * grey + (s * n['sat'] + n.get('tint', 0)) * (1 - grey)
                    light = t['light'](l) * grey + n['light'](l) * (1 - grey)
                    # El tono de los grises es el neutro; el de los colores, el de su familia (mezcla en RGB).
                    c1 = colorsys.hls_to_rgb(t['hue'] / 360, max(0, min(1, light)), max(0, min(1, sat)))
                    c0 = colorsys.hls_to_rgb(n['hue'] / 360, max(0, min(1, light)), max(0, min(1, sat)))
                    f = w / total
                    rr += (c1[0] * grey + c0[0] * (1 - grey)) * f
                    gg += (c1[1] * grey + c0[1] * (1 - grey)) * f
                    bb += (c1[2] * grey + c0[2] * (1 - grey)) * f
                hit = 0xff000000 | round(rr * 255) << 16 | round(gg * 255) << 8 | round(bb * 255)
                cache[key] = hit
            out.setPixel(x, y, hit)
    return out, peaks
