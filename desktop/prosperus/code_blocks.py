# SPDX-License-Identifier: GPL-3.0-only
"""Bloques de código de las notas: fondo propio, letra monoespaciada y colores por lenguaje.

Los colores salen de Pygments (unos 500 lenguajes: python, java, c, bash, sql…). Sin Pygments
los bloques conservan el fondo y la letra, solo sin colores."""
from PySide6.QtGui import QColor, QFont, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextFormat

try:
    from pygments.lexers import get_lexer_by_name
    from pygments.token import Comment, Keyword, Name, Number, Operator, String
    from pygments.util import ClassNotFound
    KINDS = ((Comment, 'comment'), (String, 'string'), (Number, 'number'), (Keyword, 'keyword'),
             (Name.Function, 'function'), (Name.Class, 'class'), (Name.Builtin, 'builtin'),
             (Name.Decorator, 'decorator'), (Operator, 'operator'))
except ImportError:  # pragma: no cover - Pygments es opcional
    get_lexer_by_name, KINDS = None, ()

# Paleta suave, la misma que la consola (kitty.conf).
COLOURS = {'keyword': '#96ba8c', 'string': '#d6be82', 'comment': '#7a8478', 'number': '#ba8cba',
           'function': '#7ea0c4', 'class': '#82b8b4', 'builtin': '#82b8b4', 'decorator': '#ba8cba',
           'operator': '#c8c6bc'}




def highlight_spans(code, language):
    """Colour spans for a code block: list of (start, length, kind) with offsets into `code`.
    Unknown language or empty code -> []."""
    if not code or not language or get_lexer_by_name is None:
        return []
    try:
        lexer = get_lexer_by_name(language.strip().lower(), stripnl=False, ensurenl=False)
    except ClassNotFound:
        return []
    spans = []; offset = 0
    for ttype, value in lexer.get_tokens(code):
        kind = next((kind for token_type, kind in KINDS if ttype in token_type), None)
        if kind and value:
            spans.append((offset, len(value), kind))
        offset += len(value)
    return spans


def loose_fences(markdown):
    """En el teclado español la comilla invertida es una tecla muerta: se aceptan también
    \'\'\'python o ´´´python (comillas simples o tildes) para abrir y cerrar un bloque.
    Dentro de un bloque ``` de verdad no se toca nada (un docstring \'\'\' sigue siendo código)."""
    import re
    loose = re.compile(r"^[ \t]{0,3}(?:'{3,}|´{3,})[ \t]*([\w+#.-]*)[ \t]*$")
    real = re.compile(r'^[ \t]{0,3}(```|~~~)')
    lines, inside = markdown.split('\n'), None
    for i, line in enumerate(lines):
        if inside in ('```', '~~~'):
            if line.strip().startswith(inside):
                inside = None
            continue
        match = loose.match(line)
        if match:
            lines[i] = '```' + (match.group(1) if inside is None else '')
            inside = None if inside else 'loose'
        elif inside is None and real.match(line):
            inside = real.match(line).group(1)
    return '\n'.join(lines)


def separate_fences(markdown):
    """Qt une dos bloques de código seguidos del mismo lenguaje (no marca dónde empieza cada uno):
    se separan con un párrafo invisible."""
    import re
    markdown = loose_fences(markdown)
    return re.sub(r'(?m)^(```|~~~)[ \t]*\n[ \t]*\n(?=(?:```|~~~))', '\\1\n\n\u200b\n\n', markdown)


def code_groups(document):
    """Bloques de código seguidos con el mismo lenguaje: [(primer bloque, último bloque, lenguaje)]."""
    groups, block = [], document.begin()
    while block.isValid():
        fmt = block.blockFormat()
        if fmt.hasProperty(QTextFormat.Property.BlockCodeFence):
            language = fmt.property(QTextFormat.Property.BlockCodeLanguage) or ''
            if groups and groups[-1][1].next() == block and groups[-1][2] == language:
                groups[-1][1] = block
            else:
                groups.append([block, block, language])
        block = block.next()
    return [tuple(g) for g in groups]


def style_code(document, colors):
    """Da formato a los bloques de código de un documento ya cargado con setMarkdown."""
    mono = QFont('DejaVu Sans Mono'); mono.setStyleHint(QFont.StyleHint.Monospace)
    background = QColor(colors.card); background.setAlpha(210)
    for first, last, language in code_groups(document):
        cursor = QTextCursor(document)
        cursor.setPosition(first.position())
        cursor.setPosition(last.position() + last.length() - 1, QTextCursor.MoveMode.KeepAnchor)
        frame = QTextBlockFormat(); frame.setBackground(background)
        frame.setLeftMargin(6); frame.setRightMargin(6)
        cursor.mergeBlockFormat(frame)
        # Aire alrededor del bloque: separa el código del texto de arriba y de abajo.
        for block, side in ((first, 'top'), (last, 'bottom')):
            edge = QTextCursor(block); spacing = QTextBlockFormat()
            spacing.setTopMargin(10) if side == 'top' else spacing.setBottomMargin(14)
            edge.mergeBlockFormat(spacing)
        base = QTextCharFormat(); base.setFont(mono); base.setFontPointSize(10.5)
        base.setForeground(QColor(colors.text))
        cursor.mergeCharFormat(base)
        code = cursor.selectedText().replace('\u2029', '\n')
        for start, length, kind in highlight_spans(code, language):
            span = QTextCursor(document)
            span.setPosition(first.position() + start)
            span.setPosition(first.position() + start + length, QTextCursor.MoveMode.KeepAnchor)
            tone = QTextCharFormat(); tone.setForeground(QColor(COLOURS[kind]))
            if kind == 'comment':
                tone.setFontItalic(True)
            if kind == 'keyword':
                tone.setFontWeight(QFont.Weight.DemiBold)
            span.mergeCharFormat(tone)
