import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "finalize_trust_center_links_v71.py"


def load_module():
    spec = importlib.util.spec_from_file_location("finalize_trust_center_links_v71", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TrustCenterLinkFinalizerTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.site = Path(self.temp.name) / "_site"
        page = self.site / "trust" / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text(
            '<nav><a href="/">الرئيسية</a>'
            '<a href="/encyclopedia/">الموسوعة</a>'
            '<a href="/care-guides/">أدلة التعامل</a>'
            '<a href="/daily-tools/">الأدوات اليومية</a></nav>',
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_removes_links_to_sections_missing_from_current_build(self):
        result = self.module.finalize(self.site)
        text = (self.site / "trust" / "index.html").read_text(encoding="utf-8")
        self.assertIn('/', text)
        self.assertIn('/encyclopedia/', text)
        self.assertNotIn('/care-guides/', text)
        self.assertNotIn('/daily-tools/', text)
        self.assertEqual(len(result["removed_optional_links"]), 2)

    def test_keeps_optional_link_when_target_exists(self):
        target = self.site / "care-guides" / "index.html"
        target.parent.mkdir(parents=True)
        target.write_text("ok", encoding="utf-8")
        result = self.module.finalize(self.site)
        text = (self.site / "trust" / "index.html").read_text(encoding="utf-8")
        self.assertIn('/care-guides/', text)
        self.assertNotIn('/daily-tools/', text)
        self.assertEqual(
            result["removed_optional_links"],
            ["/daily-tools/"],
        )

    def test_is_idempotent(self):
        self.module.finalize(self.site)
        first = (self.site / "trust" / "index.html").read_text(encoding="utf-8")
        second_result = self.module.finalize(self.site)
        second = (self.site / "trust" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual(second_result["removed_optional_links"], [])


if __name__ == "__main__":
    unittest.main()
