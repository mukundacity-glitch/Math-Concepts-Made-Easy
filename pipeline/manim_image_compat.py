"""Small Pillow/Manim 0.19 compatibility shim for *blank* RGBA canvas creation.

Manim's Cairo camera uses Image.fromarray(np.zeros((h,w)), mode="RGBA")
while Pillow 12 rejects a 2D float array with 4-channel mode. A raster
channel emblem activates this previously unused image-compositing path.

Only intercept that impossible-for-real-image 2D float RGBA case; every
valid RGB/RGBA numpy array continues through Pillow unmodified.
"""
from __future__ import annotations


def ensure_manim_image_pillow_compat() -> None:
    import numpy as np
    from PIL import Image

    current = Image.fromarray
    if getattr(current, "_mcme_blank_rgba_compat", False):
        return
    try:
        current(np.zeros((2, 2)), mode="RGBA")
        return  # Pillow version still supports Manim's legacy allocation.
    except ValueError as err:
        if "Invalid mode for data type" not in str(err):
            raise

    def compatible_fromarray(array, mode=None):
        if (
            mode == "RGBA"
            and isinstance(array, np.ndarray)
            and array.ndim == 2
            and array.dtype.kind == "f"
        ):
            # Manim 0.19's Cairo camera creates a transparent scratch layer.
            # The previous np.zeros array has no meaningful RGB channels.
            return Image.new("RGBA", (array.shape[1], array.shape[0]),
                             (0, 0, 0, 0))
        return current(array, mode=mode)

    compatible_fromarray._mcme_blank_rgba_compat = True
    Image.fromarray = compatible_fromarray
