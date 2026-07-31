from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from seo_agent_fleet_v334 import (  # noqa: E402
    AGENT_TYPES,
    AiDiscoveryAgent,
    SiteContext,
    canonicalize_url,
    discovery_llms,
    discovery_policy_json,
    discovery_robots,
    og_locale,
    parse_robots,
    run_fleet,
    safe_json_for_html,
)

BASE = "https://healthrenewal.org/"


def page_html(
    *,
    title: str,
    description: str,
    canonical: str,
    h1: str,
    body: str,
    robots: str = "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1",
    extra_head: str = "",
    extra_body: str = "",
) -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": canonical,
    }
    if canonical == BASE:
        schema = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "Organization", "name": "المنصة", "url": BASE},
                {"@type": "WebSite", "name": "المنصة", "url": BASE},
            ],
        }
    return f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="ar" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:locale" content="ar_JO">
<meta property="og:image" content="{BASE}assets/social-card.png">
<meta name="twitter:image" content="{BASE}assets/social-card.png">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
{extra_head}</head><body><main><h1>{h1}</h1><p>{body}</p>{extra_body}</main></body></html>"""


class Fixture:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def close(self) -> None:
        self.tmp.cleanup()

    def write_valid(self) -> None:
        body = " ".join(["محتوى عربي موثوق ومفيد يشرح الموضوع بصورة واضحة ومنهجية ومهنية للمستخدم والقارئ"] * 12)
        (self.root / "section").mkdir(parents=True)
        (self.root / "index.html").write_text(
            page_html(
                title="منصة الصحة النفسية وذوي الاحتياجات الخاصة",
                description="بوابة عربية مؤسسية موثقة تجمع المعرفة النفسية والأدلة التطبيقية والمراجع الأصلية وموارد الأشخاص ذوي الاحتياجات الخاصة.",
                canonical=BASE,
                h1="منصة الصحة النفسية وذوي الاحتياجات الخاصة",
                body=body,
                extra_body='<a href="section/">القسم العلمي</a>',
            ),
            encoding="utf-8",
        )
        section_url = BASE + "section/"
        (self.root / "section" / "index.html").write_text(
            page_html(
                title="القسم العلمي المتخصص | المنصة",
                description="قسم علمي عربي يقدم محتوى موثقًا ومراجع واضحة وإرشادات عملية ضمن ضوابط السلامة والمراجعة المهنية المستمرة.",
                canonical=section_url,
                h1="القسم العلمي المتخصص",
                body=body,
                extra_body='<a href="../">العودة إلى الرئيسية</a>',
            ),
            encoding="utf-8",
        )
        (self.root / "sitemap-index.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>{BASE}sitemap-family-core.xml</loc></sitemap></sitemapindex>',
            encoding="utf-8",
        )
        (self.root / "sitemap-family-core.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE}</loc></url><url><loc>{section_url}</loc></url></urlset>',
            encoding="utf-8",
        )
        (self.root / "robots.txt").write_text(
            f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap-index.xml\n",
            encoding="utf-8",
        )
        (self.root / "llms.txt").write_text(discovery_llms(BASE), encoding="utf-8")


class UtilityTests(unittest.TestCase):
    def test_og_locale_preserves_language_case(self) -> None:
        self.assertEqual(og_locale("ar-JO"), "ar_JO")
        self.assertEqual(og_locale("EN-us"), "en_US")

    def test_safe_json_escapes_script_breakout_characters(self) -> None:
        value = {"text": "</script><script>alert(1)</script>&"}
        serialized = safe_json_for_html(value)
        self.assertNotIn("</script>", serialized)
        self.assertIn("\\u003c", serialized)
        self.assertIn("\\u0026", serialized)
        self.assertEqual(json.loads(serialized), value)

    def test_canonicalize_removes_query_and_fragment(self) -> None:
        self.assertEqual(
            canonicalize_url("HTTPS://Example.COM/a//b/?x=1#top"),
            "https://example.com/a/b/",
        )

    def test_robots_specific_group_overrides_wildcard(self) -> None:
        policy = parse_robots(
            "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n"
        )
        self.assertTrue(policy.root_allowed("Googlebot"))
        self.assertFalse(policy.root_allowed("GPTBot"))


class FleetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Fixture()
        self.fixture.write_valid()

    def tearDown(self) -> None:
        self.fixture.close()

    def load(self) -> SiteContext:
        return SiteContext.load(self.fixture.root, BASE)

    def test_exactly_eight_agents_are_registered(self) -> None:
        self.assertEqual(len(AGENT_TYPES), 8)
        self.assertEqual(len({agent.name for agent in AGENT_TYPES}), 8)

    def test_valid_fixture_has_no_critical_findings(self) -> None:
        report = run_fleet(self.load())
        self.assertEqual(report.counts["critical"], 0, report.to_json())
        self.assertEqual(report.page_count, 2)
        self.assertEqual(len(report.agents), 8)

    def test_conflicting_index_directives_are_critical(self) -> None:
        path = self.fixture.root / "section" / "index.html"
        text = path.read_text(encoding="utf-8").replace(
            'content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"',
            'content="index,noindex,follow"',
        )
        path.write_text(text, encoding="utf-8")
        report = run_fleet(self.load())
        self.assertTrue(any(f.code == "ROBOTS_CONFLICT_INDEX" and f.severity == "critical" for f in report.findings))

    def test_invalid_jsonld_is_critical(self) -> None:
        path = self.fixture.root / "section" / "index.html"
        text = path.read_text(encoding="utf-8")
        start = text.index('<script type="application/ld+json">')
        end = text.index("</script>", start)
        text = text[:start] + '<script type="application/ld+json">{"@context":</script>' + text[end + 9 :]
        path.write_text(text, encoding="utf-8")
        report = run_fleet(self.load())
        self.assertTrue(any(f.code == "JSONLD_INVALID" and f.severity == "critical" for f in report.findings))

    def test_broken_internal_link_is_reported(self) -> None:
        path = self.fixture.root / "index.html"
        text = path.read_text(encoding="utf-8").replace(
            "</main>", '<a href="missing-page/">صفحة مفقودة</a></main>'
        )
        path.write_text(text, encoding="utf-8")
        report = run_fleet(self.load())
        self.assertTrue(any(f.code == "BROKEN_INTERNAL_LINK" for f in report.findings))

    def test_ai_search_bot_block_is_critical(self) -> None:
        (self.fixture.root / "robots.txt").write_text(
            f"User-agent: *\nAllow: /\n\nUser-agent: OAI-SearchBot\nDisallow: /\nSitemap: {BASE}sitemap-index.xml\n",
            encoding="utf-8",
        )
        findings = AiDiscoveryAgent().run(self.load())
        self.assertTrue(any(f.code == "AI_SEARCH_BLOCKED" and "OAI-SearchBot" in f.message for f in findings))

    def test_missing_page_from_sitemap_is_reported(self) -> None:
        sitemap = self.fixture.root / "sitemap-family-core.xml"
        sitemap.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE}</loc></url></urlset>',
            encoding="utf-8",
        )
        report = run_fleet(self.load())
        self.assertTrue(any(f.code == "SITEMAP_PAGE_MISSING" for f in report.findings))


class DiscoveryGenerationTests(unittest.TestCase):
    def test_allow_all_policy_keeps_search_and_training_open(self) -> None:
        robots = discovery_robots(BASE, allow_training=True)
        policy = parse_robots(robots)
        self.assertTrue(policy.root_allowed("OAI-SearchBot"))
        self.assertTrue(policy.root_allowed("GPTBot"))
        self.assertIn(f"Sitemap: {BASE}sitemap-index.xml", robots)

    def test_training_can_be_disabled_without_blocking_search(self) -> None:
        robots = discovery_robots(BASE, allow_training=False)
        policy = parse_robots(robots)
        self.assertTrue(policy.root_allowed("OAI-SearchBot"))
        self.assertFalse(policy.root_allowed("GPTBot"))
        self.assertFalse(policy.root_allowed("Applebot-Extended"))

    def test_policy_json_is_valid_and_explicit(self) -> None:
        policy = json.loads(discovery_policy_json(BASE, allow_training=True))
        self.assertEqual(policy["public_content_access"], "allowed")
        self.assertEqual(policy["search_and_answer_access"], "allowed")
        self.assertEqual(policy["training_and_model_improvement_access"], "allowed")
        self.assertIn("OAI-SearchBot", policy["search_and_answer_user_agents"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
