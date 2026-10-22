"""Permanent user-provided channel emblem must brand every Manim slide."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "remotion/public/branding/math-concepts-made-easy-logo.webp"
SHA256 = "466db2f838a17ef9978ccf79bd0459622bf20704904e0f2db0c52d28fe9c61f0"


def _template_ast():
    path = ROOT / "pipeline/cell4_animation.py"
    tree = ast.parse(path.read_text(encoding="utf8"))
    value = next(ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id == "MANIM_SCENE_CODE"
                     for target in node.targets))
    return ast.parse(value), value


def test_canonical_logo_is_committed_webp_with_exact_source_digest():
    assert LOGO.is_file(), "user-provided canonical logo is missing from git checkout"
    raw = LOGO.read_bytes()
    assert 3000 < len(raw) < 150000
    assert raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    assert hashlib.sha256(raw).hexdigest() == SHA256


def test_all_nine_production_manim_scenes_include_actual_raster_logo():
    astree, embedded = _template_ast()
    scene_classes = [
        n for n in astree.body if isinstance(n, ast.ClassDef)
        and n.name.startswith("Scene") and len(n.name) > 7
    ]
    assert len(scene_classes) == 9, [n.name for n in scene_classes]
    for scene in scene_classes:
        body = next(n for n in scene.body
                    if isinstance(n, ast.FunctionDef) and n.name == "construct")
        symbols = [
            node.func.id for node in ast.walk(body)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        expected = ("brand_logo" if scene.name in ("Scene01_Opening", "Scene09_Summary")
                    else "make_header")
        assert expected in symbols, scene.name
    assert "ImageMobject(str(BRAND_LOGO_PATH))" in embedded
    assert "Group(bg_bar, accent, logo_grp" in embedded
    assert "Group(logo_grp, ch_stack)" in embedded
    assert "logo_circ = Circle(radius=0.30" not in embedded
    assert "logo_circ = Circle(radius=0.42" not in embedded
    assert "raise FileNotFoundError" in embedded
    assert 'Path(r"__REPO_ROOT__") / "remotion"' in embedded


def test_remotion_branding_reuses_same_file_in_header_and_scaffold():
    comp = (ROOT / "remotion/src/components/BrandLogo.tsx").read_text()
    header = (ROOT / "remotion/src/components/BrandHeader.tsx").read_text()
    diag = (ROOT / "remotion/src/scaffold/ScaffoldDiagnostics.tsx").read_text()
    assert "branding/math-concepts-made-easy-logo.webp" in comp
    assert "staticFile(BRAND_LOGO_ASSET)" in comp
    assert "<BrandLogo size={72}/>" in header
    assert "<BrandLogo size={72}/>" in diag
    for path in ["TitleCard.tsx", "SceneFrame.tsx", "OutroCard.tsx"]:
        assert "<BrandHeader" in (
            ROOT / "remotion/src/components" / path).read_text()
