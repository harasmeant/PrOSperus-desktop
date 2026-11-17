# SPDX-License-Identifier: GPL-3.0-only
"""Fórmulas LaTeX de las notas → texto con <sub>/<sup> que Qt sabe mostrar."""
import os
import tempfile
import unittest
from unittest import mock

from prosperus.math_text import convert, math_to_html, mathtext_dialect


class MathTextTests(unittest.TestCase):
    def test_common_formulas(self):
        self.assertEqual(convert(r'\vec g = \dfrac{\vec F}{m}'), '<i>g⃗</i> = <i>F⃗</i>/<i>m</i>')
        self.assertEqual(convert(r'6{,}67\cdot10^{-11}\ \text{kg}'), '6,67·10<sup>−11</sup> kg')
        self.assertEqual(convert(r'v=\sqrt{\frac{2GM}{R}}'), '<i>v</i>=√(2<i>G</i><i>M</i>/<i>R</i>)')
        self.assertEqual(convert(r'\begin{pmatrix}0&-1\\1&0\end{pmatrix}'), '(0 −1 ; 1 0)')
        self.assertEqual(convert(r'm\times n'), '<i>m</i>×<i>n</i>')

    def test_code_and_prices_untouched(self):
        note = 'Cuesta 5$ y 3$; $a$\n\n```\n$x$\n```\n`$y$`'
        self.assertEqual(math_to_html(note), 'Cuesta 5$ y 3$; <i>a</i>\n\n```\n$x$\n```\n`$y$`')

    def test_display_formula_gets_its_own_paragraph(self):
        self.assertIn('\n\n  <i>E</i>=', math_to_html('Texto\n$$\nE=mc^2\n$$\nmás'))

    def test_mathtext_dialect(self):
        self.assertEqual(mathtext_dialect(r'\frac12 + \tfrac{\sqrt2}{2} \le \sqrt r'),
                         r'\dfrac{1}{2} + \dfrac{\sqrt{2}}{2} \leq \sqrt{r}')

    def test_fractions_become_images_and_matrices_stay_text(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest('sin matplotlib')
        with tempfile.TemporaryDirectory() as cache, mock.patch.dict(os.environ, {'XDG_CACHE_HOME': cache}):
            out = math_to_html(r'$\frac12 m$ y $A=\begin{pmatrix}1&0\\0&1\end{pmatrix}$', '#dddddd')
            self.assertRegex(out, r'^<img src="file://.+\.png" width="\d+" style="vertical-align: middle"/> y <i>A</i>=\(')


if __name__ == '__main__':
    unittest.main()
