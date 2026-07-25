from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stabilize_provider_layout_v225",
    ROOT / "scripts" / "stabilize_provider_layout_v225.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class StabilizeProviderLayoutV225Tests(unittest.TestCase):
    def make_root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        demo = root / "provider-assessment-demo"
        demo.mkdir(parents=True)
        (demo / "index.html").write_text(
            '<html data-institutional-contract="2026.07.25-v220"><body>'
            '<script src="activation.js"></script>'
            '<script data-institutional-contract-v220 src="institutional-contract-v220-integration.js"></script>'
            '</body></html>',
            encoding="utf-8",
        )
        (demo / "activation.js").write_text(
            '''"use strict";
(() => {
  const patchStaticCopy = () => {
    document.title = "منصة التقييم وإدارة السجلات | مصطلحات علم النفس";
  };
  const installRecordsView = () => {};
  const renderProfessionalRecords = () => {};
  installRecordsView();
  patchStaticCopy();
  renderProfessionalRecords();
})();
''',
            encoding="utf-8",
        )
        return temp, root

    def test_injects_newer_contract_guard_and_preserves_records_runtime(self):
        temp, root = self.make_root()
        self.addCleanup(temp.cleanup)
        report = MODULE.stabilize(root)
        self.assertTrue(report["changed"])
        source = (root / "provider-assessment-demo/activation.js").read_text(encoding="utf-8")
        self.assertIn(MODULE.MARKER, source)
        self.assertIn('dataset.institutionalContract === "2026.07.25-v220"', source)
        self.assertIn("script[data-institutional-contract-v220]", source)
        self.assertIn("installRecordsView();", source)
        self.assertIn("renderProfessionalRecords();", source)

    def test_second_run_is_idempotent(self):
        temp, root = self.make_root()
        self.addCleanup(temp.cleanup)
        MODULE.stabilize(root)
        before = (root / "provider-assessment-demo/activation.js").read_text(encoding="utf-8")
        report = MODULE.stabilize(root)
        after = (root / "provider-assessment-demo/activation.js").read_text(encoding="utf-8")
        self.assertFalse(report["changed"])
        self.assertEqual(before, after)
        self.assertEqual(after.count(MODULE.MARKER), 1)

    def test_missing_v220_page_contract_fails(self):
        temp, root = self.make_root()
        self.addCleanup(temp.cleanup)
        page = root / "provider-assessment-demo/index.html"
        page.write_text('<html><script src="activation.js"></script></html>', encoding="utf-8")
        with self.assertRaises(SystemExit):
            MODULE.stabilize(root)

    def test_ambiguous_activation_contract_fails(self):
        temp, root = self.make_root()
        self.addCleanup(temp.cleanup)
        runtime = root / "provider-assessment-demo/activation.js"
        runtime.write_text(runtime.read_text(encoding="utf-8").replace(MODULE.NEEDLE, ""), encoding="utf-8")
        with self.assertRaises(SystemExit):
            MODULE.stabilize(root)


if __name__ == "__main__":
    unittest.main()
