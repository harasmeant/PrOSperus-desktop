# SPDX-License-Identifier: GPL-3.0-only
"""Ramas procedurales del mapa. Base: enredadera (como la incrustación «árbol de la vida» de una guitarra):
monocromas, con curva en S, zarcillos en espiral, hojas con nervio y brotes."""
import math
import random

from PySide6.QtCore import QPointF, Qt
from functools import lru_cache

from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen


def cubic_points(p0, c1, c2, p1, steps=32):
    points = []
    for i in range(steps + 1):
        t = i / steps; u = 1 - t
        points.append(p0 * (u ** 3) + c1 * (3 * u * u * t) + c2 * (3 * u * t * t) + p1 * (t ** 3))
    return points


def tapered(points, start_width, end_width):
    """Contorno relleno de una polilínea cuyo grosor pasa de start_width a end_width."""
    left, right, last = [], [], len(points) - 1
    for i, point in enumerate(points):
        a, b = points[max(0, i - 1)], points[min(last, i + 1)]
        dx, dy = b.x() - a.x(), b.y() - a.y()
        length = math.hypot(dx, dy) or 1
        normal = QPointF(-dy / length, dx / length)
        half = (start_width + (end_width - start_width) * (i / last if last else 0)) / 2
        left.append(point + normal * half); right.append(point - normal * half)
    path = QPainterPath(left[0])
    for point in left[1:] + right[::-1]:
        path.lineTo(point)
    path.closeSubpath()
    return path


def spiral_points(base, angle, size, turn, steps=28):
    """Zarcillo: sale en la dirección angle y se enrosca (turn = ±1) cerrándose sobre sí mismo."""
    points, point, heading = [base], QPointF(base), angle
    step = size / steps * 2.2
    for i in range(steps):
        u = i / steps
        heading += turn * (.1 + .62 * u * u)   # cada vez más cerrado
        point = point + QPointF(math.cos(heading), math.sin(heading)) * step * (1 - .7 * u)
        points.append(point)
    return points


def leaf_paths(base, angle, size):
    """Hoja puntiaguda (contorno) y su nervio central."""
    direction = QPointF(math.cos(angle), math.sin(angle))
    side = QPointF(-direction.y(), direction.x())
    tip = base + direction * size
    leaf = QPainterPath(base)
    leaf.cubicTo(base + direction * size * .25 + side * size * .42, tip - direction * size * .3 + side * size * .2, tip)
    leaf.cubicTo(tip - direction * size * .3 - side * size * .2, base + direction * size * .25 - side * size * .42, base)
    vein = QPainterPath(base + direction * size * .08)
    vein.quadTo(base + direction * size * .5 + side * size * .05, tip - direction * size * .15)
    return leaf, vein


def _heading(points, i):
    a, b = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
    return math.atan2(b.y() - a.y(), b.x() - a.x())


def sparkle(painter, centre, size, color):
    """Destello de cuatro puntas."""
    path = QPainterPath(centre + QPointF(0, -size))
    for a, b in (((size * .18, -size * .18), (size, 0)), ((size * .18, size * .18), (0, size)),
                 ((-size * .18, size * .18), (-size, 0)), ((-size * .18, -size * .18), (0, -size))):
        path.lineTo(centre + QPointF(*a)); path.lineTo(centre + QPointF(*b))
    painter.setBrush(color); painter.drawPath(path)


def mushroom(painter, base, angle, size, color, spots):
    """Seta que crece desde la rama en la dirección angle; sombrero con motas recortadas."""
    up = QPointF(math.cos(angle), math.sin(angle)); side = QPointF(-up.y(), up.x())
    top = base + up * size * .75
    painter.setBrush(color); painter.drawPath(tapered([base, base + up * size * .4, top], size * .22, size * .16))
    cap = QPainterPath(top - side * size * .55)
    cap.cubicTo(top - side * size * .55 + up * size * .62, top + side * size * .55 + up * size * .62, top + side * size * .55)
    cap.quadTo(top, top - side * size * .55)
    for k in range(2):
        dot = QPainterPath(); dot.addEllipse(top + up * size * .28 + side * size * (-.2 + .38 * k), size * .08, size * .08)
        cap = cap.subtracted(dot)
    painter.drawPath(cap)


def square_spiral_points(base, angle, size, turn):
    """Greca: espiral cuadrada que gira 90° en cada tramo, cada vez más corto."""
    points, point, heading = [base], QPointF(base), angle
    for factor in (1, .75, .75, .5, .5, .3, .3):
        point = point + QPointF(math.cos(heading), math.sin(heading)) * size * factor * .5
        points.append(point); heading += turn * math.pi / 2
    return points


def diamond_paths(base, angle, size):
    """Rombo (hoja geométrica) y su nervio."""
    direction = QPointF(math.cos(angle), math.sin(angle)); side = QPointF(-direction.y(), direction.x())
    tip = base + direction * size
    middle = base + direction * size * .45
    diamond = QPainterPath(base)
    for point in (middle + side * size * .3, tip, middle - side * size * .3):
        diamond.lineTo(point)
    diamond.closeSubpath()
    vein = QPainterPath(base + direction * size * .12); vein.lineTo(tip - direction * size * .12)
    return diamond, vein


def dot(painter, centre, radius, color):
    path = QPainterPath(); path.addEllipse(centre, radius, radius)
    painter.setBrush(color); painter.drawPath(path)


def lily_path(base, angle, size):
    """Lirio art nouveau: capullo alargado entre dos pétalos que se abren hacia fuera."""
    up = QPointF(math.cos(angle), math.sin(angle)); side = QPointF(-up.y(), up.x())
    tip = base + up * size * 1.25
    path = QPainterPath(base)
    path.cubicTo(base + side * size * .35 + up * size * .4, tip + side * size * .18 - up * size * .25, tip)
    path.cubicTo(tip - side * size * .18 - up * size * .25, base - side * size * .35 + up * size * .4, base)
    for sign in (1, -1):
        petal = QPainterPath(base + up * size * .2)
        petal.cubicTo(base + side * sign * size * .7 + up * size * .2, base + side * sign * size * .85 + up * size * .75,
                      base + side * sign * size * .55 + up * size * 1.0)
        petal.cubicTo(base + side * sign * size * .5 + up * size * .55, base + side * sign * size * .25 + up * size * .35, base + up * size * .2)
        path = path.united(petal)
    return path


def peacock_eye(base, angle, size):
    """Ojo de pluma de pavo real: gota con anillo hueco y pupila."""
    up = QPointF(math.cos(angle), math.sin(angle)); side = QPointF(-up.y(), up.x())
    def drop(scale, lift):
        start = base + up * size * lift
        tip = start + up * size * scale
        path = QPainterPath(start)
        path.cubicTo(start + side * size * .55 * scale + up * size * .1, tip + side * size * .45 * scale, tip)
        path.cubicTo(tip - side * size * .45 * scale, start - side * size * .55 * scale + up * size * .1, start)
        return path
    outer, ring_hole = drop(1.0, 0), drop(.62, .22)
    pupil = QPainterPath(); pupil.addEllipse(base + up * size * .58, size * .13, size * .17)
    return outer.subtracted(ring_hole).united(pupil)


def _upward(heading, turn):
    """Ángulo perpendicular a la rama que apunta hacia arriba de la pantalla (las setas crecen hacia arriba)."""
    a, b = heading + math.pi / 2, heading - math.pi / 2
    return a if math.sin(a) < math.sin(b) else b


def feather_paths(base, angle, length, turn):
    """Pluma: cálamo afilado y vexilo asimétrico con barbas recortadas."""
    up = QPointF(math.cos(angle), math.sin(angle)); side = QPointF(-up.y(), up.x()) * turn
    tip = base + up * length
    vane = QPainterPath(base + up * length * .12)
    vane.cubicTo(base + up * length * .35 + side * length * .2, tip - up * length * .25 + side * length * .14, tip)
    vane.cubicTo(tip - up * length * .3 - side * length * .1, base + up * length * .3 - side * length * .14, base + up * length * .12)
    # Barbas: muescas finas en diagonal que dan la textura de pluma.
    for k in range(5):
        at = base + up * length * (.3 + k * .13)
        notch = QPainterPath(at + side * length * .2)
        notch.lineTo(at + side * length * .04 + up * length * .05)
        notch.lineTo(at + side * length * .2 + up * length * .025)
        notch.closeSubpath()
        vane = vane.subtracted(notch)
    shaft = [base, base + up * length * .5, tip]
    return vane, shaft


# Piezas que se pueden elegir como adorno en la aplicación «Ramas» (además de imágenes propias).
BUILTIN_ORNAMENTS = {'pluma': 'Pluma', 'seta': 'Seta', 'lirio': 'Lirio', 'pavo': 'Ojo de pavo real',
                     'zarcillo': 'Zarcillo', 'hoja': 'Hoja', 'greca': 'Greca', 'rombo': 'Rombo', 'destello': 'Destello'}


@lru_cache(maxsize=48)
def _ornament_image(path, modified, pixels, rgba):
    """Imagen escalada a `pixels` de alto; teñida del color de las ramas si rgba no es None."""
    image = QImage(path)
    if image.isNull():
        return None
    image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    image = image.scaledToHeight(max(4, pixels), Qt.TransformationMode.SmoothTransformation)
    if rgba is not None:
        # Silueta monocroma: se conserva la forma (alfa) y se pinta con el color de las ramas.
        tinter = QPainter(image)
        tinter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        tinter.fillRect(image.rect(), QColor.fromRgba(rgba))
        tinter.end()
    return image


def draw_image(painter, path, anchor, angle, height, color, tint, bottom):
    """Imagen girada para que su «arriba» apunte en angle; apoyada en anchor por abajo o centrada."""
    try:
        modified = path.stat().st_mtime_ns
    except OSError:
        return
    image = _ornament_image(str(path), modified, round(height), color.rgba() if tint else None)
    if image is None:
        return
    painter.save()
    painter.translate(anchor)
    painter.rotate(math.degrees(angle) + 90)
    painter.setOpacity(painter.opacity() * (color.alphaF() if not tint else 1))
    painter.drawImage(QPointF(-image.width() / 2, -image.height() if bottom else -image.height() / 2), image)
    painter.restore()


def ornament(painter, item, base, heading, angle, turn, size, width, color, soft):
    """Un adorno en base, orientado en angle: pegado a la rama («rama») o al final de un tallo («brote»)."""
    kind = item.get('kind')
    if item.get('place') == 'brote':
        reach = size * 1.6
        anchor = base + QPointF(math.cos(angle), math.sin(angle)) * reach
        bend = QPointF(-math.sin(angle), math.cos(angle)) * reach * .3 * turn
        stem = cubic_points(base, base + QPointF(math.cos(heading), math.sin(heading)) * reach * .4 + bend,
                            anchor - bend * .5, anchor, 14)
        painter.setBrush(color); painter.drawPath(tapered(stem, width * .5, width * .2))
        angle, bottom = _heading(stem, len(stem) - 1), False
    else:
        anchor, bottom = base, True
    if kind == 'imagen':
        draw_image(painter, item['path'], anchor, angle, size * 2.2, soft, item.get('tint', True), bottom)
        return
    painter.setBrush(soft)
    if kind == 'pluma':
        vane, shaft = feather_paths(anchor, angle, size * 3, turn)
        painter.drawPath(vane); painter.setBrush(color); painter.drawPath(tapered(shaft, max(1.0, width * .35), .3))
    elif kind == 'seta':
        mushroom(painter, anchor, angle, size * 1.4, soft, True)
    elif kind == 'lirio':
        painter.drawPath(lily_path(anchor, angle, size * 1.05))
    elif kind == 'pavo':
        painter.drawPath(peacock_eye(anchor, angle, size * 1.3))
    elif kind == 'zarcillo':
        painter.setBrush(color); painter.drawPath(tapered(spiral_points(anchor, angle, size * 2, turn), width * .35, .4))
    elif kind == 'hoja':
        leaf, _ = leaf_paths(anchor, angle, size * 1.2); painter.drawPath(leaf)
    elif kind == 'greca':
        painter.setBrush(color); painter.drawPath(tapered(square_spiral_points(anchor, angle, size * 1.3, turn), width * .35, width * .3))
    elif kind == 'rombo':
        diamond, _ = diamond_paths(anchor, angle, size * 1.1); painter.drawPath(diamond)
    elif kind == 'destello':
        sparkle(painter, anchor + QPointF(math.cos(angle), math.sin(angle)) * size * .6, size * .55, soft)


def ornament_spacing(density):
    """Frecuencia 0..1 → píxeles entre adornos (0 = nunca; 1 = cada 6 px)."""
    return None if density <= 0 else 6 / density ** 1.5


def place_ornaments(painter, items, points, start_width, end_width, color, size, seed):
    """Reparte cada adorno a lo largo de la rama según su frecuencia, con ángulo, lado, orden y gradientes."""
    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.hypot(b.x() - a.x(), b.y() - a.y()))
    total = lengths[-1]
    if total < 1:
        return
    for j, item in enumerate(items):
        spacing = ornament_spacing(item.get('density', .3))
        if spacing is None:
            continue
        # Desfase por adorno y por rama para que distintos adornos no caigan en el mismo sitio.
        offset = spacing * ((j * .37 + seed * .13) % 1)
        stations = []
        position, n = offset, 0
        while position <= total and len(stations) < 240:
            stations.append((position, n)); position += spacing; n += 1
        if item.get('order') == 'dentro':
            stations.reverse()  # lo de fuera se dibuja primero: lo de dentro queda encima
        lerp = lambda key, t: item.get(key, 0) + (item.get(key + '_end', item.get(key, 0)) - item.get(key, 0)) * t
        for position, n in stations:
            i = max(1, bisect_index(lengths, position))
            frac = (position - lengths[i - 1]) / ((lengths[i] - lengths[i - 1]) or 1)
            base = points[i - 1] + (points[i] - points[i - 1]) * frac
            t = position / total
            heading = math.atan2(points[i].y() - points[i - 1].y(), points[i].x() - points[i - 1].x())
            side = item.get('side', 'horario')
            turn = 1 if side == 'horario' or (side == 'ambos' and n % 2 == 0) else -1
            angle = heading + turn * math.radians(lerp('angle', t))
            tone = QColor(color); tone.setAlphaF(max(0.0, min(1.0, color.alphaF() * lerp('opacity', t))))
            soft = QColor(tone); soft.setAlphaF(tone.alphaF() * .85)
            width = start_width + (end_width - start_width) * t
            ornament(painter, item, base, heading, angle, turn, size * lerp('size', t), width, tone, soft)


def bisect_index(lengths, position):
    low, high = 0, len(lengths) - 1
    while low < high:
        middle = (low + high) // 2
        if lengths[middle] < position:
            low = middle + 1
        else:
            high = middle
    return low


def branch(painter, start, end, start_width, end_width, color, seed=0, sprigs=3, curl=.18, traits=None):
    """Rama procedural en un solo color. traits (del fondo) mezcla enredadera orgánica y
    geométrico (straight, filigrana art déco), regula los brotes (detail) y añade setas y destellos (magic)."""
    traits = traits or {}
    straight, detail, glow = traits.get('straight', 0), traits.get('detail', .4), traits.get('magic', 0)
    rng = random.Random(traits.get('seed', 0) * 7919 + seed)
    # Retoques personales (aplicación «Ramas»): curvatura y grosor.
    curl *= traits.get('curl', 1)
    start_width *= traits.get('width', 1); end_width *= traits.get('width', 1)
    direction = end - start
    length = math.hypot(direction.x(), direction.y()) or 1
    side = QPointF(-direction.y(), direction.x()) * (curl * (1 if seed % 2 else -1))
    # Curva en S (orgánica) mezclada con un arco de compás (geométrico) según la rectitud.
    curve = cubic_points(start, start + direction * .33 + side, start + direction * .66 - side, end)
    bow = QPointF(-direction.y(), direction.x()) * (curl * .9)
    arc = cubic_points(start, start + direction * .3 + bow, start + direction * .7 + bow, end)
    points = [c * (1 - straight) + a * straight for c, a in zip(curve, arc)]
    if glow:
        # Latigazo art nouveau: la curva se tensa al principio y se enrosca cerca del final.
        # Mismo sentido de giro en todas las ramas: las vecinas no se cruzan.
        swirl = QPointF(-direction.y(), direction.x()) * curl
        whip = cubic_points(start, start + direction * .2 + swirl * 1.3, start + direction * .85 - swirl * .7, end)
        points = [p * (1 - glow) + w * glow for p, w in zip(points, whip)]
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    band = tapered(points, start_width, end_width)
    if straight > .5:
        # Doble línea art déco: la banda queda hueca por dentro.
        band = band.subtracted(tapered(points, start_width * .45, end_width * .3))
    painter.drawPath(band)
    soft = QColor(color); soft.setAlpha(int(color.alpha() * .8))
    dark = QColor(0, 0, 0, 120)
    size = max(8.0, min(17.0, length * .07))
    count = max(1, round(sprigs * (.6 + .8 * detail + .6 * glow)))
    for k in range(count):
        t = .22 + k * (.6 / max(1, count - 1)) if count > 1 else .55
        i = int(t * (len(points) - 1))
        base, heading = points[i], _heading(points, i)
        turn = 1 if (k + seed) % 2 else -1
        width = start_width + (end_width - start_width) * t
        roll = rng.random()
        if roll < glow * .75:
            # Brote art nouveau: tallo largo y sinuoso que acaba en seta, lirio, ojo de pavo real o zarcillo.
            kind = (k + seed) % 4
            if kind == 0:
                mushroom(painter, base, _upward(heading, turn), size * 1.4, soft, True)
                continue
            stem_angle = heading + turn * .5
            reach = size * 1.6
            stem_end = base + QPointF(math.cos(stem_angle), math.sin(stem_angle)) * reach
            bend = QPointF(-math.sin(stem_angle), math.cos(stem_angle)) * reach * .35 * turn
            stem = cubic_points(base, base + QPointF(math.cos(heading), math.sin(heading)) * reach * .5 + bend,
                                stem_end - bend * .5, stem_end, 16)
            painter.setBrush(color); painter.drawPath(tapered(stem, width * .55, width * .2))
            end_angle = _heading(stem, len(stem) - 1)
            if kind == 1:
                painter.setBrush(soft); painter.drawPath(lily_path(stem_end, end_angle, size * 1.05))
            elif kind == 2:
                painter.setBrush(soft); painter.drawPath(peacock_eye(stem_end, end_angle, size * 1.3))
            else:
                painter.drawPath(tapered(spiral_points(stem_end, end_angle, size * 2.2, turn), width * .3, .4))
            # Perlas a lo largo del tallo.
            for t in (.35, .6):
                dot(painter, stem[int(t * (len(stem) - 1))] + bend * .25, width * .28, soft)
            continue
        if roll < straight:
            # Brote geométrico: tallo recto, punto de compás y greca o rombo con nervio.
            stem_angle = heading + turn * .38
            stem_end = base + QPointF(math.cos(stem_angle), math.sin(stem_angle)) * size * .8
            painter.setBrush(color); painter.drawPath(tapered([base, stem_end], width * .5, width * .35))
            dot(painter, base, width * .55, color)
            if (k + seed) % 2:
                painter.drawPath(tapered(square_spiral_points(stem_end, stem_angle, size * 1.3, turn), width * .35, width * .3))
            else:
                diamond, vein = diamond_paths(stem_end, stem_angle, size * 1.1)
                painter.setBrush(soft); painter.drawPath(diamond)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(dark, .8)); painter.drawPath(vein); painter.setPen(Qt.PenStyle.NoPen)
            small, _ = diamond_paths(base, heading - turn * .42, size * .5)
            painter.setBrush(soft); painter.drawPath(small)
            continue
        # Tallo corto, con poco ángulo, que acaba en zarcillo o en hoja.
        stem_angle = heading + turn * .38
        stem_end = base + QPointF(math.cos(stem_angle), math.sin(stem_angle)) * size * .9
        stem = cubic_points(base, base + QPointF(math.cos(heading), math.sin(heading)) * size * .4, stem_end, stem_end, 10)
        painter.setBrush(color); painter.drawPath(tapered(stem, width * .55, width * .3))
        if (k + seed) % 3 == 1:
            painter.drawPath(tapered(spiral_points(stem_end, stem_angle, size * 1.7, turn), width * .35, .5))
        else:
            leaf, vein = leaf_paths(stem_end, stem_angle - turn * .1, size * 1.15)
            painter.setBrush(soft); painter.drawPath(leaf)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(dark, .8)); painter.drawPath(vein)
            painter.setPen(Qt.PenStyle.NoPen)
        small, _ = leaf_paths(base, heading - turn * .42, size * .55)
        painter.setBrush(soft); painter.drawPath(small)
    # Adornos propios (aplicación «Ramas»): repartidos por la longitud de la rama.
    if traits.get('ornaments'):
        place_ornaments(painter, traits['ornaments'], points, start_width, end_width, color, size, seed)
    # Destellos alrededor de la rama según el brillo del fondo.
    for _ in range(round(glow * 3)):
        i = rng.randrange(len(points))
        offset = QPointF(rng.uniform(-1, 1), rng.uniform(-1, 1)) * size * 1.4
        sparkle(painter, points[i] + offset, size * rng.uniform(.25, .5), soft)
    # Brote final junto al nodo: zarcillo o greca.
    i = int(.9 * (len(points) - 1))
    turn = -1 if seed % 2 else 1
    painter.setBrush(color)
    if straight < .5:
        painter.drawPath(tapered(spiral_points(points[i], _heading(points, i) + .4, size * .7, turn), max(1.0, end_width * .6), .4))
    else:
        painter.drawPath(tapered(square_spiral_points(points[i], _heading(points, i) + .4, size * .8, turn), max(.9, end_width * .4), .8))


vine = branch
