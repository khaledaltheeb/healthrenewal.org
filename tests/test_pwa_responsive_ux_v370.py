from __future__ import annotations

import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NORMALIZER_PATH = ROOT / "scripts" / "normalize_pwa_ux_v370.py"


def load_normalizer():
    spec = importlib.util.spec_from_file_location("normalize_pwa_ux_v370", NORMALIZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load PWA UX normalizer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"Invalid PNG: {path}")
    return struct.unpack(">II", data[16:24])


class PwaResponsiveUxContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.normalizer = load_normalizer()

    def make_fixture(self, root: Path) -> None:
        required = (
            "assets/brand/pwa-192.png",
            "assets/brand/pwa-512.png",
            "assets/brand/pwa-maskable-512.png",
            "assets/platform/platform-ux-v370.css",
            "assets/platform/platform-ux-v370.js",
            "manifest.webmanifest",
        )
        for relative in required:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")

        (root / "index.html").write_text(
            """<!doctype html>
<html lang="ar" dir="rtl">
<head>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-VLZMV8Y4JP"></script>
<meta name="viewport" content="width=device-width">
<meta name="theme-color" content="#000000">
<link rel="manifest" href="old.webmanifest">
<link rel="apple-touch-icon" href="old.svg">
</head>
<body><main><table><tr><td>قيمة</td></tr></table></main></body>
</html>
""",
            encoding="utf-8",
        )
        strict = root / "provider-assessment-demo" / "professional-console.html"
        strict.parent.mkdir(parents=True, exist_ok=True)
        strict.write_text(
            "<!doctype html><html lang='ar' dir='rtl'><head></head><body><main></main></body></html>",
            encoding="utf-8",
        )
        (root / "google-verification.html").write_text(
            "google-site-verification: token",
            encoding="utf-8",
        )

    def test_normalizer_is_idempotent_and_preserves_analytics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_fixture(root)
            verification_before = (root / "google-verification.html").read_bytes()

            first = self.normalizer.apply(root)
            first_html = (root / "index.html").read_text(encoding="utf-8")
            second = self.normalizer.apply(root)
            second_html = (root / "index.html").read_text(encoding="utf-8")

            self.assertEqual(first["status"], "passed")
            self.assertEqual(second["counts"].get("current"), 2)
            self.assertEqual(first_html, second_html)
            self.assertEqual(first_html.count("G-VLZMV8Y4JP"), 1)
            self.assertEqual(first_html.count("pt-pwa-ux:v370:start"), 1)
            self.assertEqual(first_html.count("manifest.webmanifest"), 1)
            self.assertEqual(first_html.count("pwa-192.png"), 2)
            self.assertIn("viewport-fit=cover", first_html)
            self.assertIn("data-pt-ux-v370=\"true\"", first_html)
            self.assertEqual(
                verification_before,
                (root / "google-verification.html").read_bytes(),
            )

    def test_strict_application_keeps_single_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_fixture(root)
            self.normalizer.apply(root)
            html = (
                root / "provider-assessment-demo" / "professional-console.html"
            ).read_text(encoding="utf-8")
            self.assertIn("platform-ux-v370.css", html)
            self.assertNotIn("platform-ux-v370.js", html)
            self.assertIn("manifest.webmanifest", html)

    def test_manifest_and_install_icons_are_complete(self) -> None:
        manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["id"], "/")
        self.assertEqual(manifest["start_url"], "/")
        self.assertEqual(manifest["scope"], "/")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["theme_color"], "#075f5b")
        self.assertFalse(manifest["prefer_related_applications"])

        icons = {(item["src"], item.get("purpose")) for item in manifest["icons"]}
        self.assertIn(("/assets/brand/pwa-192.png", "any"), icons)
        self.assertIn(("/assets/brand/pwa-512.png", "any"), icons)
        self.assertIn(("/assets/brand/pwa-maskable-512.png", "maskable"), icons)
        self.assertEqual(
            png_dimensions(ROOT / "assets/brand/pwa-192.png"),
            (192, 192),
        )
        self.assertEqual(
            png_dimensions(ROOT / "assets/brand/pwa-512.png"),
            (512, 512),
        )
        self.assertEqual(
            png_dimensions(ROOT / "assets/brand/pwa-maskable-512.png"),
            (512, 512),
        )

    def test_service_worker_has_real_offline_contract(self) -> None:
        text = (ROOT / "scripts" / "finalize_pwa_v14.py").read_text(encoding="utf-8")
        required = (
            "healthrenewal-v24-resilient-core",
            "const OFFLINE='/offline/';",
            "Required offline assets missing",
            "navigationPreload.enable",
            "caches.match(OFFLINE",
            "write_offline_page",
            "normalize_pwa_ux_before_registration",
            "pwa-v24.json",
        )
        for marker in required:
            self.assertIn(marker, text)
        self.assertNotIn("pterminology-v23-resilient-core", text)
        self.assertNotIn("cache.addAll(CORE", text)

    def test_responsive_and_install_interactions_are_accessible(self) -> None:
        css = (ROOT / "assets" / "platform" / "platform-ux-v370.css").read_text(
            encoding="utf-8"
        )
        js = (ROOT / "assets" / "platform" / "platform-ux-v370.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("min-width: 42px", css)
        self.assertGreaterEqual(css.count("min-height: 44px"), 3)
        for marker in (
            "overflow-x: clip",
            "safe-area-inset",
            "prefers-reduced-motion",
            "forced-colors",
            ".pt-table-scroll",
        ):
            self.assertIn(marker, css)
        for marker in (
            "beforeinstallprompt",
            "appinstalled",
            "إضافة إلى الشاشة الرئيسية",
            "navigator.onLine",
            "event.key !== 'Escape'",
            "aria-hidden",
            "pt-table-scroll",
        ):
            self.assertIn(marker, js)


if __name__ == "__main__":
    unittest.main()
