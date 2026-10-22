"""Manim 0.19 Cairo legacy RGBA allocation must work on Pillow 12."""
from __future__ import annotations

import pytest


def test_cairo_rgba_scratch_compat_is_narrow_and_idempotent():
    pil = pytest.importorskip("PIL.Image")
    np = pytest.importorskip("numpy")
    from pipeline.manim_image_compat import ensure_manim_image_pillow_compat

    ensure_manim_image_pillow_compat()
    once = pil.fromarray
    ensure_manim_image_pillow_compat()
    assert pil.fromarray is once

    transparent = pil.fromarray(np.zeros((7, 11)), mode="RGBA")
    assert transparent.mode == "RGBA"
    assert transparent.size == (11, 7)
    assert transparent.getpixel((5, 3)) == (0, 0, 0, 0)

    # Normal actual pixels are never routed into the special scratch path.
    real = np.ones((3, 4, 3), dtype=np.uint8) * 101
    rendered = pil.fromarray(real, mode="RGB")
    assert rendered.mode == "RGB"
    assert rendered.getpixel((2, 2)) == (101, 101, 101)
