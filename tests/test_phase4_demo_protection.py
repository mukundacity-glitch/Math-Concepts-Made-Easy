"""Production protection must survive failures before demo preparation."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class DemoProtectionTests(unittest.TestCase):
    def setUp(self) -> None:
        source = Path(__file__).with_name("run_phase4_hybrid_demo.py")
        spec = importlib.util.spec_from_file_location("phase4_demo_protection", source)
        assert spec is not None and spec.loader is not None
        self.demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.demo)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.evidence = self.root / "evidence"
        for relative in self.demo.PROTECTED:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("original production content\n", encoding="utf8")
        for name, value in (("ROOT", self.root), ("EVIDENCE", self.evidence)):
            patcher = patch.object(self.demo, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_protect_passes_without_prepare_after_install_failure(self) -> None:
        self.demo.snapshot()
        self.demo.protect()
        report = json.loads((self.evidence / "production-unchanged.json").read_text())
        self.assertTrue(report["passed"])

    def test_repeated_snapshot_cannot_hide_production_changes(self) -> None:
        self.demo.snapshot()
        baseline = (self.evidence / "production-before.json").read_bytes()
        (self.root / "state/progress.json").write_text("changed", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "changed since baseline"):
            self.demo.snapshot()
        self.assertEqual(baseline, (self.evidence / "production-before.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "modified protected"):
            self.demo.protect()

    def test_repeated_unchanged_snapshot_preserves_baseline(self) -> None:
        self.demo.snapshot()
        baseline = (self.evidence / "production-before.json").read_bytes()
        self.demo.snapshot()
        self.assertEqual(baseline, (self.evidence / "production-before.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
