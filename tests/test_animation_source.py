"""Guards for the Manim scene template inside Cell 4.

The template is a string, so a typo in it survives every import and only
blows up inside `manim` — after Cells 1-3 have already spent minutes on
narration and TTS. These tests parse the template out of the file
without importing it (importing Cell 4 would try to run a render) and
check it the way Python would.
"""

import ast
import builtins
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.constants import PACING, SCENE_ORDER  # noqa: E402

CELL4 = REPO / "pipeline" / "cell4_animation.py"


def _module_constant(name):
    """Read a top-level string constant without importing the module."""
    tree = ast.parse(CELL4.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {CELL4}")


TEMPLATE = _module_constant("MANIM_SCENE_CODE")

SUBSTITUTIONS = {
    "__REPO_ROOT__": str(REPO),
    "__SCRIPT_PATH__": "/tmp/script.json",
    "__AUDIO_DIR__": "/tmp/audio",
    "__BANNER_PATH__": "/tmp/2.png",
    "__LOGO_PATH__": "/tmp/logo.png",
    "__PACING__": repr(PACING),
    "{C_BG}": "#0D1B2A",
    "{C_PRIMARY}": "#F0F4F8",
    "{C_SECOND}": "#8899AA",
    "{C_BLUE}": "#3B9EFF",
    "{C_GREEN}": "#2ECC71",
    "{C_YELLOW}": "#F6C90E",
    "{C_RED}": "#E74C3C",
    "{C_CARD}": "#1A2B3C",
}


def rendered_source():
    source = TEMPLATE
    for placeholder, value in SUBSTITUTIONS.items():
        source = source.replace(placeholder, value)
    return source


class TemplateIsValidPython(unittest.TestCase):
    def test_it_compiles(self):
        compile(rendered_source(), "<manim scene template>", "exec")

    def test_no_placeholder_survives_substitution(self):
        leftovers = re.findall(r"__[A-Z_]+__", rendered_source())
        self.assertEqual(leftovers, [])

    def test_build_manim_source_substitutes_everything_the_template_uses(self):
        """Every placeholder in the template must be replaced by Cell 4."""
        builder = CELL4.read_text(encoding="utf-8")
        builder = builder.split("def build_manim_source")[1]
        for placeholder in re.findall(r"__[A-Z_]+__|\{C_[A-Z]+\}", TEMPLATE):
            self.assertIn(placeholder, builder,
                          f"{placeholder} is never substituted")


class TemplateStructure(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(rendered_source())
        self.classes = {n.name: n for n in ast.walk(self.tree)
                        if isinstance(n, ast.ClassDef)}

    def test_one_scene_class_per_lesson_step(self):
        mapping = _module_constant("SCENE_CLASS_MAP")
        self.assertEqual(sorted(mapping), sorted(SCENE_ORDER))
        for step, class_name in mapping.items():
            self.assertIn(class_name, self.classes, f"missing class for {step}")

    def test_every_scene_can_move_its_camera(self):
        """A scene on plain `Scene` cannot pan or zoom — and every scene
        is supposed to breathe."""
        mapping = _module_constant("SCENE_CLASS_MAP")
        for class_name in mapping.values():
            bases = [b.id for b in self.classes[class_name].bases
                     if isinstance(b, ast.Name)]
            self.assertIn("MovingCameraScene", bases,
                          f"{class_name} cannot move its camera")

    def test_no_scene_calls_a_bare_wait(self):
        """`self.wait()` inside a scene is exactly the dead air this
        engine exists to remove — only the Director may hold the screen."""
        mapping = _module_constant("SCENE_CLASS_MAP")
        for class_name in mapping.values():
            source = ast.unparse(self.classes[class_name])
            self.assertNotIn("self.wait(", source,
                             f"{class_name} holds the screen still")

    def test_every_scene_ends_by_riding_out_the_narration(self):
        mapping = _module_constant("SCENE_CLASS_MAP")
        for class_name in mapping.values():
            source = ast.unparse(self.classes[class_name])
            self.assertIn("director.finish()", source,
                          f"{class_name} never hands back to the Director")

    def test_every_scene_opens_through_the_director(self):
        mapping = _module_constant("SCENE_CLASS_MAP")
        for class_name in mapping.values():
            source = ast.unparse(self.classes[class_name])
            self.assertIn("open_scene(self", source,
                          f"{class_name} bypasses the pacing engine")


#: Symbols the template legitimately gets from `from manim import *`.
#: Anything else left unresolved is a typo or a missing import — add a
#: name here only when the template really does start using it.
MANIM_SYMBOLS = {
    "Arrow", "Circle", "Circumscribe", "Create", "DL", "DOWN", "DR", "Dot",
    "Ellipse", "FadeIn", "FadeOut", "Flash", "GrowArrow", "GrowFromCenter",
    "Indicate", "LEFT", "LaggedStart", "Line", "ManimColor", "MathTex",
    "MovingCameraScene", "NumberLine", "ORIGIN", "PI", "RIGHT", "Rectangle",
    "RoundedRectangle", "Scene", "Sector", "SurroundingRectangle", "TAU",
    "Text", "Transform", "UL", "UP", "VGroup", "Write", "config", "linear",
    "rate_functions",
}


class TemplateNamesResolve(unittest.TestCase):
    """Compiling proves the template parses; this proves it can run.

    A helper that was renamed, or an import dropped from the template's
    header, is invisible to `compile()` and only surfaces as a
    NameError inside Manim, one scene into a render.
    """

    def test_no_unresolved_names(self):
        tree = ast.parse(rendered_source())
        defined = set(dir(builtins)) | {"__name__", "__file__"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            elif isinstance(node, ast.arg):
                defined.add(node.arg)
            elif isinstance(node, ast.ImportFrom):
                defined.update(a.asname or a.name for a in node.names)
            elif isinstance(node, ast.Import):
                defined.update((a.asname or a.name).split(".")[0]
                               for a in node.names)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                defined.add(node.name)

        used = {n.id for n in ast.walk(tree)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        unresolved = sorted(used - defined - MANIM_SYMBOLS)
        self.assertEqual(unresolved, [],
                         f"undefined names in the scene template: {unresolved}")

    def test_everything_imported_from_pacing_exists(self):
        import pipeline.pacing as pacing
        header = TEMPLATE.split("from pipeline.pacing import (")[1]
        header = header.split(")")[0]
        for name in re.findall(r"[a-z_]+", header):
            self.assertTrue(hasattr(pacing, name),
                            f"pipeline.pacing has no {name}")


class PacingBudget(unittest.TestCase):
    def test_the_ceiling_is_stricter_than_the_review_asked_for(self):
        # The brief was "no static screen longer than 5 seconds".
        self.assertLessEqual(PACING["max_static_seconds"], 5.0)

    def test_a_beat_always_fits_inside_the_ceiling(self):
        self.assertLess(PACING["min_beat_seconds"],
                        PACING["max_static_seconds"])

    def test_camera_never_zooms_past_its_home_framing(self):
        lo, hi = PACING["camera_zoom_range"]
        self.assertLess(lo, hi)
        self.assertLessEqual(hi, 1.0)
        self.assertGreater(lo, 0.8)


if __name__ == "__main__":
    unittest.main()
