# SPDX-License-Identifier: GPL-3.0-only
import os as _os; _os.environ.pop('SWAYSOCK', None)  # los tests no deben tocar la sesión Sway real
"""Gráficas ```grafica de las notas: lectura de datos y sustitución por imagen."""
import unittest

from PySide6.QtGui import QTextDocument, QTextFormat
from PySide6.QtWidgets import QApplication

from prosperus.appearance import Palette
from prosperus.charts import insert_charts, nice_step, parse_chart, render_chart


class ChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_parse_kinds_titles_separators_and_errors(self):
        spec = parse_chart('tipo: lineas\ntítulo: Temperatura\ndía; mín; máx\nLun; 4; 12,5\nMar; 6\n')
        self.assertEqual(spec, {'kind': 'line', 'title': 'Temperatura', 'labels': ['Lun', 'Mar'],
                                'series': [('mín', [4.0, 6.0]), ('máx', [12.5, 0.0])]})
        self.assertEqual(parse_chart('tipo: tarta\nt, h, x\nA, 1, 9')['series'], [('h', [1.0])])
        for bad in ('mes, v\nEnero, mucho', 'solo una fila', 'tipo: radar\na, b\nc, 1', 'tipo: tarta\na, b\nc, -1'):
            with self.assertRaises(ValueError):
                parse_chart(bad)
        self.assertEqual(nice_step(180), 50)

    def test_blocks_become_images_and_bad_data_stays_visible(self):
        document = QTextDocument()
        from prosperus.code_blocks import separate_fences
        document.setMarkdown(separate_fences('Hola\n\n```grafica\nmes, ventas\nEnero, 3\nFebrero, 5\n```\n\n```grafica\nmes, v\nEnero, mucho\n```\n'))
        self.assertEqual(insert_charts(document, Palette(120), 400), 1)
        images, block = [], document.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fmt = it.fragment().charFormat()
                if fmt.isImageFormat():
                    images.append(fmt.toImageFormat().name())
                it += 1
            block = block.next()
        self.assertEqual(images, ['grafica:0'])
        self.assertIn('⚠ Valor no numérico', document.toPlainText())
        self.assertNotIn('Febrero, 5', document.toPlainText())
        image = render_chart(parse_chart('tipo: tarta\na, b\nx, 1\ny, 3'), 300, Palette(120))
        self.assertEqual((image.width(), image.height()), (300, 186))


if __name__ == '__main__':
    unittest.main()
