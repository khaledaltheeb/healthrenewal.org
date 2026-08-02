import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "normalize_internal_base_paths_v198.py"

spec = importlib.util.spec_from_file_location("base_paths_v198", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class InternalBasePathsV198Tests(unittest.TestCase):
    def make_site(self, root: Path) -> None:
        (root / "api").mkdir(parents=True)
        (root / "assets").mkdir(parents=True)
        for route in ("trust", "encyclopedia", "tips"):
            target = root / route / "index.html"
            target.parent.mkdir(parents=True)
            target.write_text(f"<html><title>{route}</title></html>", encoding="utf-8")

        (root / "index.html").write_text(
            '''<!doctype html><html><head>
<link rel="canonical" href="https://khaledaltheeb.github.io/care-guides/">
<meta property="og:url" content="https://khaledaltheeb.github.io/start-here/">
<link rel="manifest" href="/manifest.webmanifest">
</head><body>
<a href="/care-guides/">الأدلة</a>
<a href="https://khaledaltheeb.github.io/pterminology-site/start-here/">ابدأ</a>
<a href="https://example.org/care-guides/">خارجي</a>
<a href="/guides/evaluate-mental-health-information/">دليل تقييم معلومات الصحة النفسية</a>
<a href="/search/">ابحث في الموقع</a>
<a href="/blog/">استعرض المقالات</a>
<p>أريد قراءة تحليل أعمق</p>
<p>استخدم المدونة للمقالات التحليلية وتبسيط الدراسات وتصحيح المفاهيم، مع فصل واضح بين الدليل والرأي.</p>
<img src=/assets/logo.svg alt="">
<style>.hero{background:url(/assets/hero.svg)}</style>
</body></html>''',
            encoding="utf-8",
        )
        (root / "sitemap.xml").write_text(
            '''<?xml version="1.0"?><urlset><url><loc>https://khaledaltheeb.github.io/care-guides/</loc></url></urlset>''',
            encoding="utf-8",
        )
        (root / "manifest.webmanifest").write_text(
            json.dumps(
                {
                    "start_url": "/",
                    "scope": "/",
                    "icons": [{"src": "/assets/icon.png"}],
                }
            ),
            encoding="utf-8",
        )
        (root / "assets" / "app.js").write_text(
            '''const route="/start-here/";
const api="https://khaledaltheeb.github.io/api/info.json";
const escaped=value.replace(/"/g,'&quot;');
const blogPattern=/blog/;
''',
            encoding="utf-8",
        )

    def test_normalizes_base_paths_and_repairs_only_missing_destinations(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.make_site(site)
            report = module.normalize_site(site)
            self.assertEqual(report["status"], "passed")
            self.assertGreaterEqual(report["replacements"], 8)
            self.assertGreaterEqual(report["missing_route_replacements"], 3)
            self.assertEqual(report["remaining_error_files"], 0)
            self.assertEqual(len(report["active_route_repairs"]), 3)

            html = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn(
                "https://healthrenewal.org/care-guides/",
                html,
            )
            self.assertIn('href="/care-guides/"', html)
            self.assertIn('href="/manifest.webmanifest"', html)
            self.assertIn('src=/assets/logo.svg', html)
            self.assertIn('url(/assets/hero.svg)', html)
            self.assertIn("https://example.org/care-guides/", html)
            self.assertNotIn(
                "https://khaledaltheeb.github.io/pterminology-site/pterminology-site/",
                html,
            )

            self.assertIn('href="/trust/"', html)
            self.assertIn("مركز الثقة ومنهجية تقييم المحتوى", html)
            self.assertIn('href="/encyclopedia/"', html)
            self.assertIn("ابحث في الموسوعة", html)
            self.assertIn('href="/tips/"', html)
            self.assertIn("استعرض النصائح والمحتوى التثقيفي", html)
            self.assertNotIn("/guides/evaluate-mental-health-information/", html)
            self.assertNotIn("/search/", html)
            self.assertNotIn("/blog/", html)

            manifest = json.loads((site / "manifest.webmanifest").read_text(encoding="utf-8"))
            self.assertEqual(manifest["start_url"], "/")
            self.assertEqual(manifest["scope"], "/")
            self.assertEqual(manifest["icons"][0]["src"], "/assets/icon.png")

            script = (site / "assets" / "app.js").read_text(encoding="utf-8")
            self.assertIn('"/start-here/"', script)
            self.assertIn(
                "https://healthrenewal.org/api/info.json",
                script,
            )
            self.assertIn('replace(/"/g,\'&quot;\')', script)
            self.assertIn("const blogPattern=/blog/;", script)
            self.assertNotIn("/pterminology-site/", script)

    def test_does_not_rewrite_a_route_when_the_original_target_exists(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.make_site(site)
            search = site / "search" / "index.html"
            search.parent.mkdir(parents=True)
            search.write_text("<html><title>Search</title></html>", encoding="utf-8")
            report = module.normalize_site(site)
            self.assertEqual(report["status"], "passed")
            active = {item["missing"] for item in report["active_route_repairs"]}
            self.assertNotIn("/search/", active)
            html = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="/search/"', html)
            self.assertIn("ابحث في الموقع", html)

    def test_is_idempotent_and_writes_audit_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.make_site(site)
            first = module.normalize_site(site)
            second = module.normalize_site(site)
            self.assertGreater(first["replacements"], 0)
            self.assertEqual(second["replacements"], 0)
            self.assertEqual(second["files_changed"], 0)
            stored = json.loads(
                (site / "api" / "internal-base-paths-v198.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored["status"], "passed")
            self.assertEqual(stored["required_base_path"], "/")

    def test_check_only_fails_to_hide_bad_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.make_site(site)
            report = module.normalize_site(site, check_only=True)
            self.assertEqual(report["status"], "failed")
            self.assertGreater(report["remaining_error_files"], 0)
            html = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn("https://khaledaltheeb.github.io/care-guides/", html)
            self.assertIn("/guides/evaluate-mental-health-information/", html)


if __name__ == "__main__":
    unittest.main()
