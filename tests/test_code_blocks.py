# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
"""Bloques de código de las notas: grupos por lenguaje y colores."""
import unittest

from PySide6.QtGui import QColor, QTextCursor, QTextDocument
from PySide6.QtWidgets import QApplication

from prosperus.appearance import Palette
from prosperus import code_blocks

MARKDOWN = 'Texto\n\n```python\ndef f():\n    return 1  # uno\n```\n\n```java\nint x = 2;\n```\n\n```\nplano\n```\n'


class CodeBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def colour_at(self, document, text):
        position = document.toPlainText().index(text) + 1
        cursor = QTextCursor(document); cursor.setPosition(position)
        return cursor.charFormat().foreground().color().name()

    def test_single_quotes_and_acute_accents_open_blocks(self):
        # Lo que se escribe con el teclado español: ''' o ´´´ en vez de ```.
        self.assertEqual(code_blocks.loose_fences("'''python\nimport os\n'''"), '```python\nimport os\n```')
        self.assertEqual(code_blocks.loose_fences('´´´ java\nint x;\n´´´'), '```java\nint x;\n```')
        # Sin cerrar: el bloque llega hasta el final, como en Markdown.
        self.assertEqual(code_blocks.loose_fences("'''python\nimport matplotlib"), '```python\nimport matplotlib')
        # Un docstring dentro de un bloque ``` de verdad no se toca.
        real = '```python\ndef f():\n    \'\'\'\n    doc\n    \'\'\'\n```'
        self.assertEqual(code_blocks.loose_fences(real), real)

    def test_groups_follow_fences_and_languages(self):
        document = QTextDocument(); document.setMarkdown(MARKDOWN)
        groups = [(first.text(), last.text(), language) for first, last, language in code_blocks.code_groups(document)]
        self.assertEqual(groups, [('def f():', '    return 1  # uno', 'python'), ('int x = 2;', 'int x = 2;', 'java'),
                                  ('plano', 'plano', '')])

    @unittest.skipIf(code_blocks.get_lexer_by_name is None, 'sin Pygments')
    def test_keywords_comments_and_unknown_languages(self):
        document = QTextDocument(); document.setMarkdown(MARKDOWN)
        colors = Palette(120)
        code_blocks.style_code(document, colors)
        self.assertEqual(self.colour_at(document, 'def'), code_blocks.COLOURS['keyword'])
        self.assertEqual(self.colour_at(document, '# uno'), code_blocks.COLOURS['comment'])
        self.assertEqual(self.colour_at(document, 'int x'), code_blocks.COLOURS['keyword'])
        self.assertEqual(self.colour_at(document, 'plano'), QColor(colors.text).name())
        self.assertEqual(code_blocks.highlight_spans('x = 1', 'lenguaje-inventado'), [])
        self.assertEqual(code_blocks.highlight_spans('', 'python'), [])


if __name__ == '__main__':
    unittest.main()
