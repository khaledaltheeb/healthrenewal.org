import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "normalize_internal_base_paths_v198.py"


class ProductionBasePathsTests(unittest.TestCase):
    def make_site(self, root: Path) -> None:
        (root / "api").mkdir(parents=True)
        for route in ("trust", "encyclopedia", "tips", "care-guides"):
            target = root / route / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"<html><title>{route}</title></html>", encoding="utf-8")
        (root / "index.html").write_text(
            '''<!doctype html><html><head>
<link rel="canonical" href="https://healthrenewal.org/care-guides/">
<link rel="manifest" href="/manifest.webmanifest">
</head><body>
<a href="/care-guides/">الأدلة</a>
<a href="/search/">ابحث في الموقع</a>
<img src=/assets/logo.svg alt="">
<style>.hero{background:url(/assets/hero.svg)}</style>
</body></html>''',
            encoding="utf-8",
        )
        (root / "manifest.webmanifest").write_text(
            json.dumps({"start_url": "/", "scope": "/", "icons": [{"src": "/assets/icon.png"}]}),
            encoding="utf-8",
        )

    def test_cli_honors_site_base_environment_without_subpath_rewrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.make_site(site)
            env = os.environ.copy()
            env["SITE_BASE"] = "https://healthrenewal.org/"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(site)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads((site / "api" / "internal-base-paths-v198.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["host"], "healthrenewal.org")
            self.assertEqual(report["required_base_path"], "/")
            self.assertEqual(report["site_base"], "https://healthrenewal.org/")
            html = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="/care-guides/"', html)
            self.assertNotIn("/pterminology-site/", html)
            manifest = json.loads((site / "manifest.webmanifest").read_text(encoding="utf-8"))
            self.assertEqual(manifest["start_url"], "/")
            self.assertEqual(manifest["scope"], "/")


if __name__ == "__main__":
    unittest.main()
