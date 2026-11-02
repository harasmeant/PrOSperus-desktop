# SPDX-License-Identifier: GPL-3.0-only
"""Ramas del mapa en estilo enredadera (como la incrustación «árbol de la vida» de una guitarra):
monocromas, con curva en S, zarcillos en espiral, hojas con nervio y brotes."""
import math

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


def vine(painter, start, end, start_width, end_width, color, seed=0, sprigs=3, curl=.18):
    """Dibuja una rama enredadera de start a end en un solo color (variando solo la opacidad)."""
    direction = end - start
    length = math.hypot(direction.x(), direction.y()) or 1
    side = QPointF(-direction.y(), direction.x()) * (curl * (1 if seed % 2 else -1))
    # Curva en S: los dos puntos de control se apartan hacia lados opuestos.
    points = cubic_points(start, start + direction * .33 + side, start + direction * .66 - side, end)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(tapered(points, start_width, end_width))
    soft = QColor(color); soft.setAlpha(int(color.alpha() * .8))
    size = max(8.0, min(17.0, length * .07))
    for k in range(sprigs):
        t = .22 + k * (.6 / max(1, sprigs - 1)) if sprigs > 1 else .55
        i = int(t * (len(points) - 1))
        base, heading = points[i], _heading(points, i)
        turn = 1 if (k + seed) % 2 else -1
        width = start_width + (end_width - start_width) * t
        # Tallo corto hacia un lado, que acaba en zarcillo o en hoja (alternando).
        stem_angle = heading + turn * .85
        stem_end = base + QPointF(math.cos(stem_angle), math.sin(stem_angle)) * size * .9
        stem = cubic_points(base, base + QPointF(math.cos(heading), math.sin(heading)) * size * .4, stem_end, stem_end, 10)
        painter.setBrush(color); painter.drawPath(tapered(stem, width * .55, width * .3))
        if (k + seed) % 3 == 1:
            curl_points = spiral_points(stem_end, stem_angle, size * 1.7, turn)
            painter.drawPath(tapered(curl_points, width * .35, .5))
        else:
            leaf, vein = leaf_paths(stem_end, stem_angle - turn * .25, size * 1.15)
            painter.setBrush(soft); painter.drawPath(leaf)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 0, 0, 90), .8)); painter.drawPath(vein)
            painter.setPen(Qt.PenStyle.NoPen)
        # Hoja pequeña del otro lado, como en la incrustación.
        small, _ = leaf_paths(base, heading - turn * .9, size * .55)
        painter.setBrush(soft); painter.drawPath(small)
    # Brote final: un pequeño zarcillo junto al nodo.
    i = int(.9 * (len(points) - 1))
    painter.setBrush(color)
    painter.drawPath(tapered(spiral_points(points[i], _heading(points, i) + .9, size * .7, -1 if seed % 2 else 1), max(1.0, end_width * .6), .4))
