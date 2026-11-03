# SPDX-License-Identifier: GPL-3.0-only
"""Gráficas de las notas: bloques ```grafica con una tabla de datos, dibujadas sin dependencias.

    ```grafica
    tipo: barras        (barras, lineas o tarta; opcional)
    titulo: Ventas      (opcional)
    mes, ventas, gastos
    Enero, 120, 80
    ```
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter, QPainterPath, QPen

# Colores de las series: la paleta suave de la consola y del código.
SERIES = ('#96ba8c', '#7ea0c4', '#d6be82', '#ba8cba', '#82b8b4', '#cc7870')
LANGUAGES = ('grafica', 'gráfica', 'chart')

# Lectura del bloque: borrador de qwen2.5-coder; corregido (no separaba por «;»).
KINDS = {'barras': 'bar', 'barra': 'bar', 'bar': 'bar', 'lineas': 'line', 'líneas': 'line', 'linea': 'line',
         'line': 'line', 'tarta': 'pie', 'quesito': 'pie', 'pie': 'pie'}
MAX_ROWS, MAX_SERIES = 60, 6


def parse_chart(text):
    """Parse a chart block written by a user in a note. Returns a dict:
    {'kind': 'bar'|'line'|'pie', 'title': str, 'labels': [str], 'series': [(name, [float])]}
    Raises ValueError with a short Spanish message when the data is not usable."""
    kind, title, rows = 'bar', '', []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.lower().startswith('tipo:'):
            value = line.split(':', 1)[1].strip().lower()
            if value not in KINDS:
                raise ValueError('Tipo de gráfica desconocido: ' + value)
            kind = KINDS[value]
            continue
        if line.lower().startswith('titulo:') or line.lower().startswith('título:'):
            title = line.split(':', 1)[1].strip()
            continue
        separator = ';' if ';' in line else ','  # con «;», la coma puede ser decimal (12,5)
        rows.append([cell.strip() for cell in line.split(separator)])
    if len(rows) < 2:
        raise ValueError('Faltan datos: una fila de cabecera y al menos una fila de valores.')
    header = rows[0]
    names = header[1:]
    if not names:
        raise ValueError('La cabecera necesita al menos una serie.')
    names = names[:MAX_SERIES]
    labels = []
    values = [[] for _ in names]
    for row in rows[1:MAX_ROWS + 1]:
        labels.append(row[0])
        for i in range(len(names)):
            cell = row[i + 1] if i + 1 < len(row) else ''
            if cell:
                try:
                    values[i].append(float(cell.replace(',', '.')))
                except ValueError:
                    raise ValueError(f'Valor no numérico en «{row[0]}»: {cell}')
            else:
                values[i].append(0.0)
    if kind == 'pie':
        values = [values[0]]
        if any(value < 0 for value in values[0]):
            raise ValueError('Una tarta no admite valores negativos.')
    return {'kind': kind, 'title': title, 'labels': labels, 'series': list(zip(names, values))}


def nice_step(span, ticks=4):
    """Paso «redondo» (1, 2, 2,5 o 5 por potencia de 10) para las líneas de la escala."""
    if span <= 0:
        return 1.0
    raw = span / ticks
    power = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 2.5, 5, 10):
        if raw <= factor * power:
            return factor * power
    return 10 * power


def number(value):
    text = f'{value:,.2f}'.rstrip('0').rstrip('.')
    return text.replace(',', ' ').replace('.', ',')  # 1 234,5 (formato español)


def render_chart(spec, width, colors):
    """Imagen de la gráfica, del ancho pedido y alto proporcional."""
    height = round(width * (.62 if spec['kind'] == 'pie' else .56))
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
    card = QColor(colors.card); card.setAlpha(215)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(card)
    p.drawRoundedRect(QRectF(0, 0, width, height), 14, 14)
    text, muted = QColor(colors.text), QColor(colors.muted)
    small = QFont('DejaVu Sans', 9); title_font = QFont('DejaVu Sans', 11, QFont.Weight.Bold)
    top = 16
    if spec['title']:
        p.setFont(title_font); p.setPen(text)
        p.drawText(QRectF(18, 12, width - 36, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, spec['title'])
        top = 44
    series = spec['series']
    legend = len(series) > 1 or spec['kind'] == 'pie'
    bottom = height - (40 if legend else 18)
    area = QRectF(18, top, width - 36, bottom - top)
    p.setFont(small)
    if spec['kind'] == 'pie':
        _pie(p, area, spec, text, colors)
    else:
        _axes_chart(p, area, spec, text, muted, small)
    if legend:
        names = spec['labels'] if spec['kind'] == 'pie' else [name for name, _ in series]
        _legend(p, QRectF(18, height - 30, width - 36, 20), names, text, small)
    p.end()
    return image


# Gráficas de barras y de líneas, con sus ejes y escala
def _axes_chart(p, area, spec, text, muted, font):
    series, labels = spec['series'], spec['labels']
    values = [v for _, vs in series for v in vs] or [0]
    low, high = min(0.0, min(values)), max(0.0, max(values))
    step = nice_step(high - low or 1)
    low, high = math.floor(low / step) * step, math.ceil(high / step) * step or step
    metrics = QFontMetrics(font)
    left = area.left() + max(metrics.horizontalAdvance(number(v)) for v in (low, high)) + 10
    plot = QRectF(left, area.top() + 6, area.right() - left, area.height() - 30)
    y = lambda v: plot.bottom() - (v - low) / (high - low) * plot.height()
    grid = QColor(muted); grid.setAlpha(60)
    tick = low
    while tick <= high + step / 2:
        p.setPen(QPen(grid, 1, Qt.PenStyle.DashLine if tick else Qt.PenStyle.SolidLine))
        p.drawLine(QPointF(plot.left(), y(tick)), QPointF(plot.right(), y(tick)))
        p.setPen(muted)
        p.drawText(QRectF(area.left(), y(tick) - 8, left - area.left() - 6, 16),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number(tick))
        tick += step
    count = max(1, len(labels))
    slot = plot.width() / count
    # Etiquetas de abajo: se saltan si no caben.
    every = max(1, math.ceil(max((metrics.horizontalAdvance(l) for l in labels), default=0) / max(slot - 6, 1)))
    p.setPen(muted)
    for i, label in enumerate(labels):
        if i % every == 0:
            p.drawText(QRectF(plot.left() + i * slot - slot * (every - 1) / 2, plot.bottom() + 6, slot * every, 18),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                       metrics.elidedText(label, Qt.TextElideMode.ElideRight, round(slot * every - 4)))
    zero = y(max(low, min(0.0, high)))
    if spec['kind'] == 'bar':
        group = slot * .74; bar = group / len(series)
        for s, (_, vs) in enumerate(series):
            colour = QColor(SERIES[s % len(SERIES)])
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(colour)
            for i, v in enumerate(vs):
                x = plot.left() + i * slot + (slot - group) / 2 + s * bar
                top, base = sorted((y(v), zero))
                p.drawRoundedRect(QRectF(x + 1, top, max(bar - 2, 1), max(base - top, 1)), 3, 3)
    else:
        for s, (_, vs) in enumerate(series):
            colour = QColor(SERIES[s % len(SERIES)])
            points = [QPointF(plot.left() + (i + .5) * slot, y(v)) for i, v in enumerate(vs)]
            path = QPainterPath()
            for i, point in enumerate(points):
                path.moveTo(point) if i == 0 else path.lineTo(point)
            p.setPen(QPen(colour, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(path)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(colour)
            for point in points:
                p.drawEllipse(point, 3.2, 3.2)


# Gráfica de tarta (en anillo) con porcentajes
def _pie(p, area, spec, text, colors):
    values = spec['series'][0][1]
    total = sum(values)
    side = min(area.width(), area.height())
    box = QRectF(area.center().x() - side / 2, area.center().y() - side / 2, side, side)
    if total <= 0:
        p.setPen(text); p.drawText(area, Qt.AlignmentFlag.AlignCenter, 'Sin valores'); return
    angle = 90.0
    edge = QColor(colors.card)
    for i, v in enumerate(values):
        sweep = -360.0 * v / total
        p.setPen(QPen(edge, 2)); p.setBrush(QColor(SERIES[i % len(SERIES)]))
        p.drawPie(box, round(angle * 16), round(sweep * 16))
        share = v / total
        if share >= .06:
            middle = math.radians(angle + sweep / 2)
            point = QPointF(box.center().x() + math.cos(middle) * side * .32, box.center().y() - math.sin(middle) * side * .32)
            p.setPen(QColor('#1d231c'))
            p.drawText(QRectF(point.x() - 30, point.y() - 9, 60, 18), Qt.AlignmentFlag.AlignCenter, f'{share * 100:.0f} %')
        angle += sweep
    # Hueco central: tarta en anillo, más ligera.
    hole = QColor(colors.card); p.setPen(Qt.PenStyle.NoPen); p.setBrush(hole)
    p.drawEllipse(box.center(), side * .16, side * .16)


# Muestra leyendas con colores y etiquetas de series
def _legend(p, rect, names, text, font):
    metrics = QFontMetrics(font)
    x = rect.left()
    for i, name in enumerate(names):
        width = metrics.horizontalAdvance(name) + 26
        if x + width > rect.right():
            break
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(SERIES[i % len(SERIES)]))
        p.drawRoundedRect(QRectF(x, rect.center().y() - 5, 10, 10), 3, 3)
        p.setPen(text)
        p.drawText(QRectF(x + 15, rect.top(), width, rect.height()), Qt.AlignmentFlag.AlignVCenter, name)
        x += width + 8


def insert_charts(document, colors, width):
    """Sustituye cada bloque ```grafica por su imagen. Si los datos no sirven, el bloque se queda
    como código con el motivo delante (para que se pueda corregir). Devuelve cuántas se dibujaron."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QTextBlockFormat, QTextCursor, QTextDocument, QTextImageFormat
    from .code_blocks import code_groups
    groups = [g for g in code_groups(document) if g[2].strip().lower() in LANGUAGES]
    drawn = 0
    for n, (first, last, _) in reversed(list(enumerate(groups))):
        cursor = QTextCursor(document)
        cursor.setPosition(first.position())
        cursor.setPosition(last.position() + last.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        source = cursor.selectedText().replace(' ', '\n')
        try:
            spec = parse_chart(source)
        except ValueError as error:
            cursor.insertText(f'⚠ {error}\n{source}')
            continue
        image = render_chart(spec, width, colors)
        name = f'grafica:{n}'
        document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), image)
        cursor.removeSelectedText()
        cursor.setBlockFormat(QTextBlockFormat())  # ya no es un bloque de código
        picture = QTextImageFormat(); picture.setName(name)
        picture.setWidth(image.width()); picture.setHeight(image.height())
        cursor.insertImage(picture)
        drawn += 1
    return drawn
