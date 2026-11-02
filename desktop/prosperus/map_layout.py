# SPDX-License-Identifier: GPL-3.0-only
import math
import bisect

def ellipse_points(count, cx, cy, rx, ry):
    if count == 0:
        return []
    sample_count = 720
    angles = [-math.pi/2 + i * 2 * math.pi / sample_count for i in range(sample_count)]
    points = []
    for a in angles:
        x = cx + rx * math.cos(a)
        y = cy + ry * math.sin(a)
        points.append((x, y))
    cum_lengths = [0.0]
    for i in range(1, sample_count):
        x1, y1 = points[i-1]
        x2, y2 = points[i]
        seg_len = math.hypot(x2 - x1, y2 - y1)
        cum_lengths.append(cum_lengths[-1] + seg_len)
    # closing segment
    x1, y1 = points[-1]
    x2, y2 = points[0]
    seg_len = math.hypot(x2 - x1, y2 - y1)
    cum_lengths.append(cum_lengths[-1] + seg_len)
    perim = cum_lengths[-1]
    step = perim / count
    result = []
    for k in range(count):
        target = k * step
        i = bisect.bisect_left(cum_lengths, target)
        if i == 0:
            result.append(points[0])
        elif i >= sample_count:
            result.append(points[-1])
        else:
            prev_len = cum_lengths[i-1]
            next_len = cum_lengths[i]
            frac = (target - prev_len) / (next_len - prev_len) if next_len != prev_len else 0.0
            x0, y0 = points[i-1]
            x1, y1 = points[i]
            x = x0 + frac * (x1 - x0)
            y = y0 + frac * (y1 - y0)
            result.append((x, y))
    return result

def separate(rects, fixed, bounds, gap, iterations=60):
    # rects and fixed are lists of (x, y, w, h)
    mov = [list(r) for r in rects]
    fix = [list(f) for f in fixed]
    bx, by, bw, bh = bounds
    for _ in range(iterations):
        moved = False
        # movable vs movable
        for i in range(len(mov)):
            for j in range(i+1, len(mov)):
                r1 = mov[i]
                r2 = mov[j]
                g2 = gap / 2.0
                r1x1, r1y1 = r1[0] - g2, r1[1] - g2
                r1x2, r1y2 = r1[0] + r1[2] + g2, r1[1] + r1[3] + g2
                r2x1, r2y1 = r2[0] - g2, r2[1] - g2
                r2x2, r2y2 = r2[0] + r2[2] + g2, r2[1] + r2[3] + g2
                ox = max(0, min(r1x2, r2x2) - max(r1x1, r2x1))
                oy = max(0, min(r1y2, r2y2) - max(r1y1, r2y1))
                if ox == 0 or oy == 0:
                    continue
                if ox <= oy:
                    # horizontal push: determine push direction based on right edge positions
                    push = ox
                    c1x = r1[0] + r1[2] / 2
                    c2x = r2[0] + r2[2] / 2
                    if c1x == c2x:
                        dir1 = -1
                    else:
                        dir1 = -1 if c1x < c2x else 1
                    r1[0] += dir1 * push / 2
                    r2[0] -= dir1 * push / 2
                else:
                    # vertical push: determine push direction based on bottom edge positions
                    push = oy
                    c1y = r1[1] + r1[3] / 2
                    c2y = r2[1] + r2[3] / 2
                    if c1y == c2y:
                        dir1 = -1
                    else:
                        dir1 = -1 if c1y < c2y else 1
                    r1[1] += dir1 * push / 2
                    r2[1] -= dir1 * push / 2
                moved = True
        # movable vs fixed
        for i in range(len(mov)):
            for f in fix:
                r1 = mov[i]
                g2 = gap / 2.0
                r1x1, r1y1 = r1[0] - g2, r1[1] - g2
                r1x2, r1y2 = r1[0] + r1[2] + g2, r1[1] + r1[3] + g2
                r2x1, r2y1 = f[0] - g2, f[1] - g2
                r2x2, r2y2 = f[0] + f[2] + g2, f[1] + f[3] + g2
                ox = max(0, min(r1x2, r2x2) - max(r1x1, r2x1))
                oy = max(0, min(r1y2, r2y2) - max(r1y1, r2y1))
                if ox == 0 or oy == 0:
                    continue
                if ox <= oy:
                    push = ox
                    c1x = r1[0] + r1[2] / 2
                    c2x = f[0] + f[2] / 2
                    if c1x == c2x:
                        dir1 = -1
                    else:
                        dir1 = -1 if c1x < c2x else 1
                    r1[0] += dir1 * push
                else:
                    push = oy
                    c1y = r1[1] + r1[3] / 2
                    c2y = f[1] + f[3] / 2
                    if c1y == c2y:
                        dir1 = -1
                    else:
                        dir1 = -1 if c1y < c2y else 1
                    r1[1] += dir1 * push
                moved = True
        # clamp all movables within bounds
        for r in mov:
            r[0] = max(bx, min(bx + bw - r[2], r[0]))
            r[1] = max(by, min(by + bh - r[3], r[1]))
        if not moved:
            break
    return [tuple(round(v) for v in r) for r in mov]

def nearest_in_direction(points, origin, direction):
    dir_angle = {
        'right': 0,
        'left': math.pi,
        'up': -math.pi/2,
        'down': math.pi/2
    }.get(direction)
    if dir_angle is None:
        return None
    best_idx = None
    best_score = float('inf')
    for idx, (px, py) in enumerate(points):
        dx = px - origin[0]
        dy = py - origin[1]
        angle = math.atan2(dy, dx)
        while angle < 0:
            angle += 2 * math.pi
        while angle >= 2 * math.pi:
            angle -= 2 * math.pi
        diff = abs(angle - dir_angle)
        diff = min(diff, 2 * math.pi - diff)
        if diff <= math.radians(60):
            dist = math.hypot(dx, dy)
            # penalize vertical offset for horizontal directions, and vice versa
            if direction in ('right', 'left'):
                off = abs(dy)
            else:
                off = abs(dx)
            score = dist + 2 * off
            if score < best_score:
                best_score = score
                best_idx = idx
    return best_idx if best_idx is not None else None


def force_layout(points, weights, cx, cy, rx, ry, iterations=150):
    """Ajusta puntos sobre una elipse con repulsión, atracción por enlaces y resorte radial."""
    if not weights:
        return points
    pts = [list(p) for p in points]
    for _ in range(iterations):
        forces = [[0.0, 0.0] for _ in pts]
        # repulsión entre todas las parejas de nodos
        for i in range(len(pts)):
            xi, yi = pts[i]
            for j in range(i + 1, len(pts)):
                xj, yj = pts[j]
                dx = xi - xj
                dy = yi - yj
                d = math.hypot(dx, dy)
                if d < 1:
                    d = 1
                strength = 9000.0 / (d * d)
                fx = dx / d * strength
                fy = dy / d * strength
                forces[i][0] += fx
                forces[i][1] += fy
                forces[j][0] -= fx
                forces[j][1] -= fy
        # atracción por enlaces ponderados
        for (i, j), w in weights.items():
            xi, yi = pts[i]
            xj, yj = pts[j]
            dx = xj - xi
            dy = yj - yi
            d = math.hypot(dx, dy)
            if d == 0:
                continue
            f = 0.02 * w * d
            forces[i][0] += dx / d * f
            forces[i][1] += dy / d * f
            forces[j][0] -= dx / d * f
            forces[j][1] -= dy / d * f
        # resorte radial hacia el punto de la elipse en el ángulo actual
        for i, (x, y) in enumerate(pts):
            angle = math.atan2(y - cy, x - cx)
            ex = cx + rx * math.cos(angle)
            ey = cy + ry * math.sin(angle)
            forces[i][0] += 0.15 * (ex - x)
            forces[i][1] += 0.15 * (ey - y)
        # aplicar fuerzas con tope de 12 px por iteración
        for i in range(len(pts)):
            fx, fy = forces[i]
            d = math.hypot(fx, fy)
            if d > 12:
                fx = fx / d * 12
                fy = fy / d * 12
            pts[i][0] += fx
            pts[i][1] += fy
    return [(x, y) for x, y in pts]


def map_metrics(width, height):
    """Medidas del mapa para una superficie: tarjetas, carpeta central y radios de la elipse.
    La elipse no pasa de 2,3 veces más ancha que alta: en 21:9 o 32:9 no se estira sin fin."""
    nw = max(134, min(190, int(width * .17)))
    nh = max(80, min(108, int(height * .21)))
    cw = max(166, min(226, int(width * .2)))
    fw, fh = max(130, min(176, int(width * .14))), 42
    lw, lh = max(104, min(150, int(width * .11))), 26
    ry = max(nh + 30, height * .36)
    rx = max(cw / 2 + nw / 2 + 24, min(width * .34, ry * 2.3))
    return {'nw': nw, 'nh': nh, 'cw': cw, 'fw': fw, 'fh': fh, 'lw': lw, 'lh': lh, 'rx': rx, 'ry': ry}


def radial_slots(count, cx, cy, rx, ry):
    """Radios equiespaciados como en el prototipo: el primero arriba y en sentido horario.
    La figura se encaja en el óvalo: con un número impar (3, 5, 7) los puntos no llegan abajo,
    así que se centra y se estira hasta tocar los bordes; el orden y la simetría no cambian."""
    if count <= 0:
        return []
    raw = [(math.cos(-math.pi / 2 + i * 2 * math.pi / count), math.sin(-math.pi / 2 + i * 2 * math.pi / count))
           for i in range(count)]
    if count < 3:
        return [(cx + rx * x, cy + ry * y) for x, y in raw]
    def fit(values):
        low, high = min(values), max(values)
        middle, half = (low + high) / 2, (high - low) / 2 or 1
        return [(v - middle) / half for v in values]
    xs, ys = fit([x for x, _ in raw]), fit([y for _, y in raw])
    return [(cx + rx * x, cy + ry * y) for x, y in zip(xs, ys)]


def concentric_slots(count, cx, cy, center_w, center_h, cell_w, cell_h, gap=22, bounds=None):
    """Huecos en anillos elípticos concéntricos alrededor del centro, de dentro afuera, sin solaparse ni salirse."""
    left, top, right, bottom = bounds or (cx - 4000, cy - 4000, cx + 4000, cy + 4000)
    taken = [(cx, cy, center_w, center_h)]
    fits = lambda x, y: (left + cell_w / 2 <= x <= right - cell_w / 2 and top + cell_h / 2 <= y <= bottom - cell_h / 2
                         and all(abs(x - ox) >= (cell_w + w) / 2 + gap or abs(y - oy) >= (cell_h + h) / 2 + gap
                                 for ox, oy, w, h in taken))
    slots, ring = [], 0
    # Anillos a medio paso: cada uno aporta los huecos que no pisan a los de dentro (quedan al tresbolillo).
    while len(slots) < count:
        rx = center_w / 2 + cell_w / 2 + gap + ring * (cell_w + gap) / 2
        ry = center_h / 2 + cell_h / 2 + gap + ring * (cell_h + gap) / 2
        # si el anillo excede los límites, romper la recursión
        if cx - rx + cell_w / 2 < left and cx + rx - cell_w / 2 > right:
            break
        ring += 1
        perimeter = math.pi * (3 * (rx + ry) - math.sqrt((3 * rx + ry) * (rx + 3 * ry)))
        for x, y in ellipse_points(max(8, int(perimeter / (cell_w * .4))), cx, cy, rx, ry):
            # verificar que no salga de bounds ni se solape con slots existentes
            if len(slots) < count and fits(x, y):
                slots.append((x, y)); taken.append((x, y, cell_w, cell_h))
    return slots


def link_order(count, weights):
    """Orden en que las notas más enlazadas quedan una junto a otra."""
    if not weights:
        return list(range(count))
    weight = lambda a, b: weights.get((min(a, b), max(a, b)), 0)
    # calcular gravedad total de cada nodo
    totals = [sum(weight(i, j) for j in range(count) if j != i) for i in range(count)]
    order = [max(range(count), key=lambda i: (totals[i], -i))]
    rest = [i for i in range(count) if i != order[0]]
    while rest:
        # seleccionar siguiente nodo: mayor conexión con el último, luego mayor gravedad, menor índice
        best = max(rest, key=lambda i: (weight(order[-1], i), max(weight(p, i) for p in order), -i))
        order.append(best); rest.remove(best)
    return order
