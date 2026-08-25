from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
EXPECTED = {
    "https://healthrenewal.org/sitemap.xml",
    "https://healthrenewal.org/sitemap-accessibility.xml",
    "https://healthrenewal.org/sitemap-aac.xml",
    "https://healthrenewal.org/sitemap-addiction-atlas.xml",
}


def main() -> None:
    index_path = ROOT / "sitemap-index.xml"
    robots_path = ROOT / "robots.txt"
    atlas_path = ROOT / "sitemap-addiction-atlas.xml"
    if not index_path.is_file() or not robots_path.is_file() or not atlas_path.is_file():
        raise SystemExit("required sitemap files are missing")

    root = ET.parse(index_path).getroot()
    locations = {
        (node.text or "").strip()
        for node in root.findall("sm:sitemap/sm:loc", NS)
    }
    missing = EXPECTED - locations
    if missing:
        raise SystemExit(f"central sitemap index is missing: {sorted(missing)}")

    robots = robots_path.read_text(encoding="utf-8")
    expected_robot_line = "Sitemap: https://healthrenewal.org/sitemap-index.xml"
    if expected_robot_line not in robots:
        raise SystemExit("robots.txt does not advertise the central sitemap index")
    if "Disallow: /" in robots:
        raise SystemExit("robots.txt contains a site-wide crawl block")

    print({
        "status": "passed",
        "indexedSitemaps": sorted(locations),
        "atlasRegistered": True,
        "robotsUsesCentralIndex": True,
    })


if __name__ == "__main__":
    main()
