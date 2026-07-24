import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_polisher():
    path = ROOT / "scripts" / "polish_site_v16.py"
    spec = importlib.util.spec_from_file_location("polish_site_v16", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load polish_site_v16.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SocialMetadataTests(unittest.TestCase):
    def test_adds_missing_page_specific_social_metadata_once(self):
        module = load_polisher()
        source = (
            '<html lang="ar" dir="rtl"><head><title>دليل عربي متخصص</title>'
            '<meta name="description" content="وصف عربي دقيق وموسع للصفحة الحالية.">'
            '</head><body><h1>دليل عربي متخصص</h1></body></html>'
        )
        result, count = module.inject_social_metadata(source, "دليل عربي متخصص")
        self.assertEqual(count, 6)
        self.assertIn('property="og:title" content="دليل عربي متخصص"', result)
        self.assertIn('property="og:description" content="وصف عربي دقيق وموسع للصفحة الحالية."', result)
        self.assertIn('property="og:type" content="website"', result)
        self.assertIn('name="twitter:card" content="summary"', result)
        self.assertIn('name="twitter:title" content="دليل عربي متخصص"', result)
        self.assertIn('name="twitter:description" content="وصف عربي دقيق وموسع للصفحة الحالية."', result)

        repeated, repeated_count = module.inject_social_metadata(
            result, "دليل عربي متخصص"
        )
        self.assertEqual(repeated_count, 0)
        self.assertEqual(repeated, result)

    def test_preserves_existing_open_graph_values(self):
        module = load_polisher()
        source = (
            '<html><head><title>صفحة اختبار</title>'
            '<meta name="description" content="وصف صفحة الاختبار.">'
            '<meta property="og:title" content="عنوان مخصص">'
            '</head><body></body></html>'
        )
        result, count = module.inject_social_metadata(source, "صفحة اختبار")
        self.assertEqual(count, 5)
        self.assertEqual(result.count('property="og:title"'), 1)
        self.assertIn('property="og:title" content="عنوان مخصص"', result)


if __name__ == "__main__":
    unittest.main()
