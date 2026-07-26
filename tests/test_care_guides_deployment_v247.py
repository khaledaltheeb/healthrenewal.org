from __future__ import annotations

import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_care_guides_deployment_v247 import (  # noqa: E402
    BASE_URL,
    BLOCKED_SLUG,
    MAXIMUM_META_DESCRIPTION,
    MINIMUM_GUIDES,
    expected_core_slugs,
    verify,
)

WORKFLOW = ROOT / ".github/workflows/verify-care-guides-live-v247.yml"


def guide_html(title: str, canonical: str, *, description: str | None = None) -> str:
    description = description or (
        "دليل عربي مؤسسي عملي يشرح الدعم الآمن والخطوات القابلة للتنفيذ ومتى يلزم طلب المساعدة المهنية أو العاجلة."
    )
    body = " ".join(
        [
            "محتوى عربي دقيق يشرح الفهم والتواصل والخطة العملية والمتابعة والسلامة ودعم الأسرة ومقدم الرعاية دون تشخيص ذاتي"
        ]
        * 90
    )
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "Article", "headline": title},
                {"@type": "HowTo", "name": title},
                {"@type": "BreadcrumbList", "itemListElement": []},
            ],
        },
        ensure_ascii=False,
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="keywords" content="دليل الرعاية النفسية, دعم الأسرة, الصحة النفسية">
<meta name="robots" content="index,follow,max-snippet:-1">
<meta name="googlebot" content="index,follow,max-snippet:-1">
<link rel="canonical" href="{canonical}">
<script type="application/ld+json">{schema}</script>
</head><body><main><h1>{title}</h1><section><h2>الفهم والخطة</h2><p>{body}</p></section>
<section><h2>مصادر مؤسسية للمراجعة</h2><p>منظمة الصحة العالمية وNICE وNHS.</p></section>
<aside>عند الخطر اتصل بخدمات الطوارئ المحلية أو جهة صحية عاجلة.</aside></main></body></html>'''


class CareGuidesDeploymentV247Tests(unittest.TestCase):
    def build_site(self, root: Path, sha: str = "a" * 40) -> list[str]:
        slugs = expected_core_slugs()
        self.assertEqual(len(slugs), MINIMUM_GUIDES)
        (root / "api").mkdir(parents=True)
        (root / "care-guides").mkdir(parents=True)
        (root / "deployment.json").write_text(
            json.dumps({"schema_version": 29, "commit": sha}, ensure_ascii=False),
            encoding="utf-8",
        )
        (root / "api/care-guides-v21.json").write_text(
            json.dumps(
                {
                    "version": 246,
                    "source_guides": 101,
                    "core_guides": 101,
                    "published_core_guides": 100,
                    "minimum_published_guides": 100,
                    "minimum_published_guides_met": True,
                    "blocked_review_slugs": [BLOCKED_SLUG],
                    "needs_specialist_review_published": False,
                    "autism_published": False,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        hub = '''<!doctype html><html lang="ar" dir="rtl"><body><main data-care-library="1">
<h1>أدلة التعامل والرعاية</h1><p>المنهجية التحريرية وضبط الجودة</p>
<script type="application/ld+json">{"@type":"CollectionPage","x":"ItemList","y":"FAQPage"}</script>
</main></body></html>'''
        (root / "care-guides/index.html").write_text(hub, encoding="utf-8")
        (root / "robots.txt").write_text(
            f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap-care-guides.xml\n",
            encoding="utf-8",
        )

        sitemap_root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        hub_url = ET.SubElement(sitemap_root, "url")
        ET.SubElement(hub_url, "loc").text = BASE_URL + "care-guides/"
        for index, slug in enumerate(slugs, start=1):
            canonical = BASE_URL + f"care-guides/{slug}/"
            page = root / "care-guides" / slug / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text(guide_html(f"دليل رعاية مؤسسي رقم {index}", canonical), encoding="utf-8")
            node = ET.SubElement(sitemap_root, "url")
            ET.SubElement(node, "loc").text = canonical
        ET.ElementTree(sitemap_root).write(
            root / "sitemap-care-guides.xml",
            encoding="utf-8",
            xml_declaration=True,
        )
        return slugs

    def test_complete_hundred_page_deployment_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="care-live-v247-") as temp:
            root = Path(temp)
            sha = "b" * 40
            slugs = self.build_site(root, sha)
            result = verify(root, expected_sha=sha, mode="live")
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["verified_core_pages"], 100)
            self.assertEqual(result["source_guides"], 101)
            self.assertTrue(result["blocked_review_route_absent"])
            self.assertTrue(result["all_indexable"])
            self.assertEqual(result["unique_titles"], 100)
            self.assertGreaterEqual(result["minimum_visible_words"], 650)
            self.assertLessEqual(result["maximum_meta_description_length"], MAXIMUM_META_DESCRIPTION)
            self.assertTrue((root / "api/care-guides-deployment-v247.json").is_file())
            self.assertNotIn(BLOCKED_SLUG, slugs)

    def test_overlong_live_meta_description_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="care-live-v247-long-meta-") as temp:
            root = Path(temp)
            sha = "c" * 40
            slugs = self.build_site(root, sha)
            slug = slugs[0]
            canonical = BASE_URL + f"care-guides/{slug}/"
            page = root / "care-guides" / slug / "index.html"
            page.write_text(
                guide_html(
                    "دليل ذو وصف طويل غير مقبول",
                    canonical,
                    description="و" * (MAXIMUM_META_DESCRIPTION + 1),
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AssertionError, "meta description length"):
                verify(root, expected_sha=sha, mode="live")

    def test_workflow_contract_is_bound_to_validated_pages_deployment(self) -> None:
        self.assertTrue(WORKFLOW.is_file())
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('workflows: ["Deploy validated main to GitHub Pages"]', text)
        self.assertIn("care-guides-live-v247", text)
        self.assertIn("--base-url", text)
        self.assertIn("--expected-sha", text)
        self.assertIn("actions/upload-artifact@v4", text)


if __name__ == "__main__":
    unittest.main()
