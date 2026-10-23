"""Inline Manim mathematics must retain the grouping of stacked fractions."""
import pytest

from pipeline.mathtext import latex_to_plain


@pytest.mark.parametrize('source, expected', [
    (r'y = \frac{x-5}{2}', 'y = (x-5)/2'),
    (r'\frac{a+b}{c+d}', '(a+b)/(c+d)'),
    (r'\frac{1}{2x}', '1/(2x)'),
    (r'\frac{\frac{1}{2}}{3}', '(1/2)/3'),
    (r'\frac{1}{\frac{x-5}{2}}', '1/((x-5)/2)'),
    (r'\tfrac{3}{4}', '3/4'),
    (r'\frac{x^{2}+1}{x-1}', '(x²+1)/(x-1)'),
    (r'\frac{x}{y^{2}}', 'x/y²'),
    (r'\frac{x^{20}}{2}', 'x²⁰/2'),
    (r'f^{-1}(x) = \frac{x-5}{2}', 'f⁻¹(x) = (x-5)/2'),
])
def test_fraction_grouping_is_preserved(source, expected):
    assert latex_to_plain(source) == expected
