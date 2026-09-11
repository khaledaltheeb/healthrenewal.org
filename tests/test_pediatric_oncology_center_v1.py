from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "materialize_pediatric_oncology_center_v1.py"
SPEC = importlib.util.spec_from_file_location("pediatric_oncology_center_v1", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def sample_payload():
    return {
        "sector": {"id": "sector", "description": "مركز"},
        "categories": [
            {"id": "root", "parent_id": None, "slug": "pediatric-cancer-types-diagnosis", "name_ar": "الأنواع والتشخيص", "description": "الجذر", "sort_order": 1},
            {"id": "leaf", "parent_id": "root", "slug": "pediatric-solid-tumors", "name_ar": "الأورام الصلبة", "description": "فرع", "sort_order": 1},
            {"id": "research", "parent_id": None, "slug": "pediatric-cancer-research-evidence", "name_ar": "الأبحاث والأدلة", "description": "بحث", "sort_order": 2},
        ],
        "items": [
            {"id": "one", "slug": "one", "title": "صفحة أولى", "excerpt": "شرح أول", "content_type": "guide", "category_id": "root", "canonical_url": "/care-guides/one/", "published_at": "2026-01-01", "arabic_word_count": 1300, "reference_count": 3, "seo_title": "سيو", "seo_description": "وصف"},
            {"id": "two", "slug": "two", "title": "صفحة ثانية", "excerpt": "شرح ثان", "content_type": "research", "category_id": "research", "canonical_url": "/magazine/pediatric-oncology/studies/two/", "published_at": "2026-01-02", "arabic_word_count": 1400, "reference_count": 4, "seo_title": "سيو", "seo_description": "وصف"},
        ],
        "relations": [
            {"content_id": "one", "category_id": "root", "is_primary": True},
            {"content_id": "one", "category_id": "leaf", "is_primary": False},
            {"content_id": "two", "category_id": "research", "is_primary": True},
        ],
        "quality": {"minimum_arabic_words": 1300, "minimum_references": 3, "duplicate_canonicals": [], "missing_titles": [], "missing_canonicals": [], "missing_seo": []},
    }


class PediatricOncologyCenterTests(unittest.TestCase):
    def test_secondary_category_counts_as_populated(self):
        model = MOD.build_model(sample_payload())
        self.assertEqual(model["aggregate"]["leaf"], {"one"})

    def test_parent_aggregates_descendants_without_duplicates(self):
        data = sample_payload()
        data["relations"].append({"content_id": "one", "category_id": "root", "is_primary": False})
        model = MOD.build_model(data)
        self.assertEqual(model["aggregate"]["root"], {"one"})

    def test_empty_active_section_blocks_publication(self):
        data = sample_payload()
        data["categories"].append({"id": "empty", "parent_id": None, "slug": "empty", "name_ar": "فارغ", "description": "فارغ", "sort_order": 9})
        with self.assertRaises(ValueError):
            MOD.build_model(data)

    def test_section_has_single_h1_indexability_and_content_cards(self):
        data = sample_payload()
        model = MOD.build_model(data)
        source = MOD.render_section(data, model, "leaf")
        self.assertEqual(source.lower().count("<h1>"), 1)
        self.assertIn('name="robots" content="index,follow', source)
        self.assertIn('rel="canonical"', source)
        self.assertIn("الصفحات المنشورة في هذا المسار", source)
        self.assertIn("شرح أول", source)


if __name__ == "__main__":
    unittest.main()
