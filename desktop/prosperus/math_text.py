# SPDX-License-Identifier: GPL-3.0-only
"""Fórmulas $...$ y $$...$$ de las notas: Qt no entiende LaTeX, así que se pasan a texto con
<sub>, <sup> y <i> (Qt sí acepta ese HTML dentro del Markdown, también en tablas).
Con matplotlib instalado, las fórmulas aparte ($$) y las que llevan fracciones o raíces se dibujan
como imagen (se guarda en caché); si no está, o la fórmula no la entiende (matrices), quedan como texto.

shortcut: mathtext de matplotlib no sabe matrices (\\begin{pmatrix}): salen en una línea, (a  b ; c  d)."""
import hashlib
import html
import os
import re
from pathlib import Path

SYMBOLS = {
    'cdot': '·', 'times': '×', 'approx': '≈', 'neq': '≠', 'le': '≤', 'leq': '≤', 'ge': '≥', 'geq': '≥',
    'pm': '±', 'propto': '∝', 'infty': '∞', 'dots': '…', 'ldots': '…', 'cdots': '⋯', 'circ': '°',
    'to': '→', 'rightarrow': '→', 'Rightarrow': '⇒', 'longrightarrow': '⟶', 'Leftrightarrow': '⇔',
    'Longleftrightarrow': '⟺', 'leftarrow': '←', 'Leftarrow': '⇐',
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε', 'varepsilon': 'ε',
    'theta': 'θ', 'lambda': 'λ', 'mu': 'μ', 'pi': 'π', 'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ',
    'varphi': 'φ', 'phi': 'φ', 'omega': 'ω', 'Delta': 'Δ', 'Sigma': 'Σ', 'Omega': 'Ω', 'Phi': 'Φ',
    'imath': 'ı', 'jmath': 'ȷ', 'sum': '∑', 'int': '∫', 'partial': '∂', 'nabla': '∇',
    'quad': ' ', 'qquad': '  ', ',': ' ', ';': ' ', ':': ' ', ' ': ' ',
    '!': '', 'left': '', 'right': '', 'displaystyle': '', '{': '{', '}': '}', '%': '%', '$': '$',
}
WORDS = {'sin', 'cos', 'tan', 'arctan', 'arcsin', 'arccos', 'log', 'ln', 'exp', 'min', 'max', 'lim'}
ACCENTS = {'vec': '⃗', 'hat': '̂', 'bar': '̅', 'dot': '̇', 'tilde': '̃'}
TEXT = {'text', 'mathrm', 'operatorname', 'textrm', 'mathbf', 'textbf'}


class _Reader:
    def __init__(self, source):
        self.s, self.i = source, 0

    def skip_spaces(self):
        while self.i < len(self.s) and self.s[self.i] == ' ':
            self.i += 1

    def raw_group(self):
        """Texto entre llaves tal cual (sin convertir); sin llaves, el siguiente carácter."""
        self.skip_spaces()
        if self.i < len(self.s) and self.s[self.i] == '{':
            depth, start = 0, self.i
            while self.i < len(self.s):
                depth += {'{': 1, '}': -1}.get(self.s[self.i], 0)
                self.i += 1
                if depth == 0:
                    return self.s[start + 1:self.i - 1]
            return self.s[start + 1:]
        self.i += 1
        return self.s[self.i - 1:self.i]

    def command(self):
        match = re.compile(r'\\([a-zA-Z]+|.)').match(self.s, self.i)
        self.i = match.end() if match else len(self.s)
        if match and match.group(1).isalpha():
            self.skip_spaces()  # como en LaTeX: el espacio tras \times o \cdot no cuenta
        return match.group(1) if match else ''

    def argument(self):
        """Un argumento ya convertido: {grupo}, \\orden o un carácter."""
        self.skip_spaces()
        if self.s.startswith('\\', self.i):
            start = self.i
            name = self.command()
            if name in ACCENTS or name in TEXT or name in ('frac', 'dfrac', 'tfrac', 'sqrt'):
                self.i = start
                return self.atom()
            return convert(self.s[start:self.i])
        return convert(self.raw_group())

    def atom(self):
        char = self.s[self.i]
        if char == '\\':
            name = self.command()
            if name in TEXT:
                return html.escape(self.raw_group())
            if name in ('frac', 'dfrac', 'tfrac'):
                return _wrap(self.argument()) + '/' + _wrap(self.argument())
            if name == 'sqrt':
                return '√' + _wrap(self.argument())
            if name in ACCENTS:
                base = self.argument()  # el acento va dentro de la cursiva, pegado a su letra
                return base[:-4] + ACCENTS[name] + '</i>' if base.endswith('</i>') else base + ACCENTS[name]
            if name == 'boxed':
                return '<b>' + self.argument() + '</b>'
            if name == 'xrightarrow':
                return '→<sup>' + self.argument() + '</sup>'
            if name == 'underbrace':
                return self.argument()
            if name == 'begin':
                return self.environment(self.raw_group())
            if name == '\\':
                return ' ; '
            if name in WORDS:
                return name
            return html.escape(SYMBOLS.get(name, name))
        self.i += 1
        if char in '^_':
            tag = 'sup' if char == '^' else 'sub'
            return f'<{tag}>{self.argument()}</{tag}>'
        if char == '{':
            self.i -= 1
            return convert(self.raw_group())
        if char == '&':
            return ' '
        if char == '-':
            return '−'
        if char.isascii() and char.isalpha():
            return f'<i>{char}</i>'
        return html.escape(char)

    def environment(self, name):
        end = self.s.find('\\end{' + name + '}', self.i)
        end = len(self.s) if end < 0 else end
        body = convert(self.s[self.i:end])
        self.i = min(len(self.s), end + len('\\end{' + name + '}'))
        if name == 'cases':
            return '{ ' + body
        return {'pmatrix': '(' + body + ')', 'bmatrix': '[' + body + ']', 'vmatrix': '|' + body + '|'}.get(name, body)


def _wrap(part):
    """Paréntesis en a/b solo si hace falta: (a+b)/2, pero m/2."""
    plain = re.sub(r'<[^>]+>', '', part)
    return f'({part})' if re.search(r'[\s+−=·×/]', plain.strip()) else part


def convert(latex):
    """Una fórmula LaTeX (sin los $) → HTML de una línea."""
    reader, out = _Reader(latex.replace('\n', ' ')), []
    while reader.i < len(reader.s):
        out.append(reader.atom())
    return ''.join(out)


FENCE = re.compile(r'(?ms)^[ \t]*(```|~~~).*?(?:^[ \t]*\1[ \t]*$|\Z)|`[^`\n]+`')
DISPLAY = re.compile(r'\$\$(.+?)\$\$', re.S)
# Como Obsidian: sin espacio tras el $ de apertura ni antes del de cierre, y sin cifra detrás (5$).
INLINE = re.compile(r'(?<![\\$])\$(?=[^\s$])([^$\n]+?)(?<=[^\s\\])\$(?![\d$])')


TALL = re.compile(r'\\[dt]?frac|\\sqrt')
SCALE = 2  # se dibuja al doble y se muestra a la mitad: nítido en pantallas HiDPI


def cache_dir():
    root = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    return root / 'prosperus' / 'formulas'


def mathtext_dialect(latex):
    """Lo que LaTeX acepta y mathtext no: \\tfrac, \\frac12, \\sqrt2, \\le. Las fracciones, siempre grandes."""
    latex = re.sub(r'\\[dt]?frac(?![a-zA-Z])', r'\\dfrac', latex)
    latex = re.sub(r'\\dfrac\s*([\w.])\s*([\w.])', r'\\dfrac{\1}{\2}', latex)
    latex = re.sub(r'\\sqrt\s*(\w)', r'\\sqrt{\1}', latex)
    return re.sub(r'\\le(?![a-zA-Z])', r'\\leq', latex)


def formula_image(latex, color, size):
    """Ruta de un PNG transparente con la fórmula, o None si no hay matplotlib o no la entiende."""
    latex = mathtext_dialect(' '.join(latex.split()))
    path = cache_dir() / (hashlib.sha1(f'{latex}|{color}|{size}'.encode()).hexdigest() + '.png')
    if not path.exists():
        try:
            from matplotlib.figure import Figure
            figure = Figure(figsize=(.01, .01))
            figure.text(0, 0, f'${latex}$', fontsize=size, color=color)
            path.parent.mkdir(parents=True, exist_ok=True)
            figure.savefig(path, dpi=72 * SCALE, transparent=True, bbox_inches='tight', pad_inches=.02)
        except Exception:  # sin matplotlib o fórmula que mathtext no sabe: se queda como texto
            path.unlink(missing_ok=True)
            return None
    return path


def _image(latex, color, size):
    path = formula_image(latex, color, size) if color else None
    if path is None:
        return None
    from PySide6.QtGui import QImageReader
    width = QImageReader(str(path)).size().width() // SCALE
    return f'<img src="{path.as_uri()}" width="{width}" style="vertical-align: middle"/>'


def math_to_html(markdown, color=None, size=13):
    """Convierte las fórmulas de una nota; el código (``` y `...`) no se toca.
    Con `color` (el del texto), las aparte ($$) y las que llevan fracciones o raíces se dibujan."""
    parts, last = [], 0
    for match in FENCE.finditer(markdown):
        parts += [_formulas(markdown[last:match.start()], color, size), match.group()]
        last = match.end()
    return ''.join(parts + [_formulas(markdown[last:], color, size)])


def _formulas(text, color, size):
    def display(m):
        latex = m.group(1).strip()
        return '\n\n  ' + (_image(latex, color, size) or convert(latex)) + '\n\n'

    def inline(m):
        latex = m.group(1)
        return (TALL.search(latex) and _image(latex, color, size)) or convert(latex)
    return INLINE.sub(inline, DISPLAY.sub(display, text))
