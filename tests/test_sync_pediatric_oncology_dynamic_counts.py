from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.sync_pediatric_oncology_dynamic_counts import LEGACY_ALIAS, synchronize


OWNER_MARKER = "<!-- rawafid:pediatric-oncology-materializer:v1 -->"


def hub_html(title: str) -> str:
    return (
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        f'<title>{title} | منصة روافد</title>'
        '<meta name="description" content="وصف تجريبي">'
        '<meta name="robots" content="index,follow">'
        '<link rel="canonical" href="https://healthrenewal.org/example/">'
        '</head><body>'
        f'{OWNER_MARKER}<main><header><h1>{title}</h1><p>وصف</p></header></main>'
        '</body></html>'
    )


class DynamicPediatricOncologyCountsTests(unittest.TestCase):
    def make_root(self, counts: tuple[int, int, int] = (6, 5, 1)) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        report = root / "api/pediatric-oncology-materialization-v1.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        records, studies, theses = counts
        report.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "passed",
                    "records": records,
                    "studies": studies,
                    "theses": theses,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        hubs = {
            "magazine/pediatric-oncology/index.html": "أبحاث سرطان الأطفال",
            "magazine/pediatric-oncology/studies/index.html": "أحدث دراسات سرطان الأطفال",
            "magazine/pediatric-oncology/theses/index.html": "الرسائل الجامعية في سرطان الأطفال",
        }
        for relative, title in hubs.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(hub_html(title), encoding="utf-8")
        return root

    def test_synchronizes_all_hubs_and_legacy_alias(self) -> None:
        root = self.make_root()
        changed = synchronize(root, check=False)
        self.assertEqual(len(changed), 4)

        root_hub = (root / "magazine/pediatric-oncology/index.html").read_text(encoding="utf-8")
        studies_hub = (root / "magazine/pediatric-oncology/studies/index.html").read_text(encoding="utf-8")
        theses_hub = (root / "magazine/pediatric-oncology/theses/index.html").read_text(encoding="utf-8")
        legacy = (root / LEGACY_ALIAS).read_text(encoding="utf-8")

        self.assertIn('data-current-count="6"', root_hub)
        self.assertIn('العدد الحالي: 6', root_hub)
        self.assertIn('data-current-count="5"', studies_hub)
        self.assertIn('العدد الحالي: 5', studies_hub)
        self.assertIn('data-current-count="1"', theses_hub)
        self.assertIn('العدد الحالي: 1', theses_hub)
        self.assertIn('<meta name="robots" content="noindex,follow">', legacy)
        self.assertIn('href="https://healthrenewal.org/magazine/pediatric-oncology/theses/"', legacy)
        self.assertIn('data-current-count="1"', legacy)

    def test_is_idempotent(self) -> None:
        root = self.make_root()
        synchronize(root, check=False)
        self.assertEqual(synchronize(root, check=False), [])
        synchronize(root, check=True)

    def test_updates_when_report_counts_change(self) -> None:
        root = self.make_root()
        synchronize(root, check=False)
        report = root / "api/pediatric-oncology-materialization-v1.json"
        report.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "passed",
                    "records": 11,
                    "studies": 7,
                    "theses": 4,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        synchronize(root, check=False)
        root_hub = (root / "magazine/pediatric-oncology/index.html").read_text(encoding="utf-8")
        theses_hub = (root / "magazine/pediatric-oncology/theses/index.html").read_text(encoding="utf-8")
        legacy = (root / LEGACY_ALIAS).read_text(encoding="utf-8")
        self.assertIn('data-current-count="11"', root_hub)
        self.assertIn('data-current-count="4"', theses_hub)
        self.assertIn('data-current-count="4"', legacy)
        self.assertNotIn('data-current-count="1"', theses_hub)

    def test_rejects_inconsistent_report(self) -> None:
        root = self.make_root((7, 5, 1))
        with self.assertRaisesRegex(RuntimeError, "Count contract mismatch"):
            synchronize(root, check=False)


if __name__ == "__main__":
    unittest.main()
