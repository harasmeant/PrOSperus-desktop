# SPDX-License-Identifier: GPL-3.0-only
"""Ramas procedurales del mapa. Base: enredadera (como la incrustación «árbol de la vida» de una guitarra):
monocromas, con curva en S, zarcillos en espiral, hojas con nervio y brotes."""
import math
import random

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen


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


def ring(painter, centre, radius, color, hole):
    """Articulación o tornillo: disco con agujero (o ranura) en el color de fondo."""
    path = QPainterPath(); path.addEllipse(centre, radius, radius)
    inner = QPainterPath(); inner.addEllipse(centre, radius * hole, radius * hole)
    painter.setBrush(color); painter.drawPath(path.subtracted(inner))


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


def _arm_points(start, end, side, steps):
    """Brazo articulado: dos tramos rectos con el codo apartado hacia un lado."""
    elbow = (start + end) / 2 + side
    half = steps // 2
    return ([start + (elbow - start) * (i / half) for i in range(half)] +
            [elbow + (end - elbow) * (i / (steps - half)) for i in range(steps - half + 1)]), elbow


def branch(painter, start, end, start_width, end_width, color, seed=0, sprigs=3, curl=.18, traits=None):
    """Rama procedural en un solo color. traits (del fondo) mezcla enredadera orgánica y brazo
    mecánico (straight), regula los brotes (detail) y añade setas y destellos (glow)."""
    traits = traits or {}
    straight, detail, glow = traits.get('straight', 0), traits.get('detail', .4), traits.get('glow', 0)
    rng = random.Random(traits.get('seed', 0) * 7919 + seed)
    direction = end - start
    length = math.hypot(direction.x(), direction.y()) or 1
    side = QPointF(-direction.y(), direction.x()) * (curl * (1 if seed % 2 else -1))
    # Curva en S (orgánica) y brazo de dos tramos (mecánico), mezclados según la rectitud del fondo.
    curve = cubic_points(start, start + direction * .33 + side, start + direction * .66 - side, end)
    # Todos los codos giran hacia el mismo lado: brazos vecinos no se cruzan.
    arm, elbow = _arm_points(start, end, QPointF(-direction.y(), direction.x()) * (curl * .8), len(curve) - 1)
    points = [c * (1 - straight) + a * straight for c, a in zip(curve, arm)]
    end_width = end_width + (start_width * .7 - end_width) * straight
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(tapered(points, start_width, end_width))
    soft = QColor(color); soft.setAlpha(int(color.alpha() * .8))
    dark = QColor(0, 0, 0, 120)
    size = max(8.0, min(17.0, length * .07))
    if straight > .5:
        # Articulaciones en el hombro y el codo.
        ring(painter, points[0] + direction * (12 / length), start_width * .9, color, .45)
        ring(painter, points[len(points) // 2], start_width * .85, color, .45)
    count = max(1, round(sprigs * (.6 + .8 * detail)))
    for k in range(count):
        t = .22 + k * (.6 / max(1, count - 1)) if count > 1 else .55
        i = int(t * (len(points) - 1))
        base, heading = points[i], _heading(points, i)
        turn = 1 if (k + seed) % 2 else -1
        width = start_width + (end_width - start_width) * t
        roll = rng.random()
        if roll < glow * .5:
            mushroom(painter, base, heading + turn * 1.2, size * 1.1, soft, True)
            continue
        if roll < straight:
            # Pieza mecánica: tornillo sobre la rama o pistón corto que acaba en articulación.
            if rng.random() < .5:
                ring(painter, base, width * .6, soft, .35)
            else:
                tip = base + QPointF(math.cos(heading + turn * .5), math.sin(heading + turn * .5)) * size
                painter.setBrush(color); painter.drawPath(tapered([base, tip], width * .45, width * .45))
                ring(painter, tip, width * .5, soft, .4)
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
    # Destellos alrededor de la rama según el brillo del fondo.
    for _ in range(round(glow * 4)):
        i = rng.randrange(len(points))
        offset = QPointF(rng.uniform(-1, 1), rng.uniform(-1, 1)) * size * 1.4
        sparkle(painter, points[i] + offset, size * rng.uniform(.25, .5), soft)
    if straight < .5:
        # Brote final junto al nodo.
        i = int(.9 * (len(points) - 1))
        painter.setBrush(color)
        painter.drawPath(tapered(spiral_points(points[i], _heading(points, i) + .4, size * .7, -1 if seed % 2 else 1), max(1.0, end_width * .6), .4))


vine = branch
