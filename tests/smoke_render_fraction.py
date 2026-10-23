"""Render through the same semantic-text factory used by full lesson boards."""
from manim import DOWN, VGroup, Scene, config
from pipeline.semantic_math import semantic_text


class FractionGroupingSmoke(Scene):
    def construct(self):
        self.camera.background_color = '#0B1F38'
        examples = [
            (r'y = \frac{x-5}{2}', 'y = (x-5)/2'),
            (r'z = \frac{a+b}{c+d}', 'z = (a+b)/(c+d)'),
            (r'f(x) = \frac{1}{2x}', 'f(x) = 1/(2x)'),
            (r'f^{-1}(x) = \frac{x-5}{2}', 'f⁻¹(x) = (x-5)/2'),
        ]
        rows = []
        for source, expected in examples:
            row = semantic_text(source, size=54, mode='math', max_width=12)
            assert row.semantic_math_display == expected
            assert row.width <= 12.01
            rows.append(row)
        group = VGroup(*rows).arrange(DOWN, buff=1)
        assert group.height < 7
        self.add(group)
