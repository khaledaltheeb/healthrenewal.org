from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
ORIGIN = "https://khaledaltheeb.github.io"
BASE_PATH = "/pterminology-site/"
TARGET_SITEMAP = f"{BASE}sitemap-developers.xml"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_sitemap_namespace() -> None:
    path = SITE / "sitemap.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    namespace = root.tag.split("}", 1)[0].strip("{") if "}" in root.tag else ""
    tag = lambda name: f"{{{namespace}}}{name}" if namespace else name
    canonical_tag = tag("sitemap")
    matches = []
    for child in list(root):
        loc = child.find("{*}loc")
        if loc is not None and (loc.text or "").strip() == TARGET_SITEMAP:
            matches.append(child)
    for child in matches:
        root.remove(child)
    sitemap = ET.SubElement(root, canonical_tag)
    ET.SubElement(sitemap, tag("loc")).text = TARGET_SITEMAP
    if namespace:
        ET.register_namespace("", namespace)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    check = ET.parse(path).getroot()
    refs = [(node.text or "").strip() for node in check.findall("{*}sitemap/{*}loc")]
    if refs.count(TARGET_SITEMAP) != 1:
        raise SystemExit("Developers sitemap namespace normalization failed")


def normalize_openapi_paths() -> None:
    path = SITE / "api" / "v1" / "openapi.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["servers"] = [{"url": ORIGIN}]
    normalized = {}
    for route, operation in payload.get("paths", {}).items():
        clean = "/" + route.lstrip("/")
        if not clean.startswith(BASE_PATH):
            clean = BASE_PATH.rstrip("/") + clean
        normalized[clean] = operation
    payload["paths"] = normalized
    write_json(path, payload)
    if len(normalized) != 4 or any(not key.startswith(BASE_PATH) for key in normalized):
        raise SystemExit(f"OpenAPI base-path normalization failed: {list(normalized)}")


def refresh_catalog_count() -> None:
    path = SITE / "api" / "v1" / "catalog.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    verification = SITE / "google644f1f7a8b7aaa2b.html"
    pages = [page for page in SITE.rglob("*.html") if page != verification]
    payload["page_count"] = len(pages)
    payload["developers_page_included"] = (SITE / "developers" / "index.html").is_file()
    write_json(path, payload)
    if payload["page_count"] < 100 or not payload["developers_page_included"]:
        raise SystemExit(f"Enterprise catalog refresh failed: {payload}")


def main() -> None:
    normalize_sitemap_namespace()
    normalize_openapi_paths()
    refresh_catalog_count()
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_enterprise_platform_v215.py"), str(SITE)],
        check=True,
    )
    print(json.dumps({"status": "passed", "sitemap_namespace": True, "openapi_base_path": BASE_PATH, "catalog_refreshed": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
