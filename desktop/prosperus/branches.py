# SPDX-License-Identifier: GPL-3.0-only
"""Ramas de árbol para el mapa: troncos que se afinan, ramitas y hojas."""
import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath


def _bezier(p0, c, p1, t):
    u = 1 - t
    return p0 * (u * u) + c * (2 * u * t) + p1 * (t * t)


def branch_path(start, control, end, start_width, end_width, steps=24):
    """Contorno relleno de una curva cuadrática cuyo grosor pasa de start_width a end_width."""
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        point = _bezier(start, control, end, t)
        # Tangente de la curva: perpendicular para abrir el grosor a cada lado.
        tangent = (control - start) * (2 * (1 - t)) + (end - control) * (2 * t)
        length = math.hypot(tangent.x(), tangent.y()) or 1
        normal = QPointF(-tangent.y() / length, tangent.x() / length)
        half = (start_width + (end_width - start_width) * t) / 2
        left.append(point + normal * half); right.append(point - normal * half)
    path = QPainterPath(left[0])
    for point in left[1:]:
        path.lineTo(point)
    for point in reversed(right):
        path.lineTo(point)
    path.closeSubpath()
    return path


def point_on(start, control, end, t):
    return _bezier(start, control, end, t)


def leaf_path(base, angle, size):
    """Hoja lanceolada que nace en base y apunta en la dirección angle (radianes)."""
    tip = base + QPointF(math.cos(angle), math.sin(angle)) * size
    side = QPointF(-math.sin(angle), math.cos(angle)) * (size * .32)
    middle = (base + tip) / 2
    path = QPainterPath(base)
    path.quadTo(middle + side, tip)
    path.quadTo(middle - side, base)
    return path
