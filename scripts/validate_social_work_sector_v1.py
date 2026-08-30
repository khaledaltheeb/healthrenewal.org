#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
SECTOR = ROOT / "evidence-guides" / "social-work"
SITEMAP = ROOT / "sitemap-social-work.xml"
BASE = "https://healthrenewal.org/evidence-guides/social-work/"
SLUGS = [
"co-created-help-plan","working-relationship","desired-outcomes","strengths-perspective","participation-and-voice","ethics-power-autonomy","multi-challenged-families","community-resource-map","child-voice-family-decisions","agreement-on-collaboration","involuntary-participation","progress-review","service-coordination","documenting-disagreement","ending-help-plan","solution-focused-conversations","home-based-family-social-work","family-engagement-barriers","school-family-collaboration","poverty-structural-barriers","rebuilding-trust-after-harm","collaborative-professional-interview","family-resilience","professional-persistence","support-network-mapping","referral-with-continuity","multidisciplinary-family-meeting","non-stigmatizing-professional-language","family-life-course-transitions","separation-divorce-family-support","older-adults-family-support","caregiver-role-burden","transition-to-adulthood","supported-decision-making","institutional-advocacy","foster-care-adoption-family-work","youth-complex-behaviour-family-work","family-conflict-decision-map","financial-crisis-family-plan","family-role-redistribution","community-partnership-family-support","service-exit-plan","help-plan-quality-audit","privacy-information-sharing","failed-referral-recovery","community-independence-plan","post-closure-follow-up","family-priority-setting","family-burden-monitoring","family-feedback-service-quality","periodic-family-plan-review","community-help-project-methodology","synergetic-collaborative-family-model","physical-activity-quality-of-life-family-support","public-transport-social-inclusion-older-adults"
]
EXPECTED = [BASE] + [BASE + slug + "/" for slug in SLUGS]
FSD_SOURCE = "https://www.fsd.uni-lj.si/mma/-/2016091213042605/"

def read(path: Path) -> str:
    if not path.is_file(): raise AssertionError(f"missing file: {path}")
    return path.read_text(encoding="utf-8")

assert len(SLUGS) == 55 and len(set(SLUGS)) == 55
pages = sorted(SECTOR.rglob("index.html"))
assert len(pages) == 56, f"expected 56 pages, found {len(pages)}"
actual_dirs = {p.parent.name for p in pages if p.parent != SECTOR}
assert actual_dirs == set(SLUGS), f"slug mismatch missing={set(SLUGS)-actual_dirs} extra={actual_dirs-set(SLUGS)}"

hub = read(SECTOR / "index.html")
assert "55 دليل" in hub, "hub count missing"
assert "warm-referral-continuity" not in hub, "broken legacy route remains in hub"
assert FSD_SOURCE in hub, "exact recommended 2016 source missing from hub"
assert "Social Chamber of Slovenia" in hub and "Slovenian Association of Social Workers" in hub, "institution distinction missing"
for slug in SLUGS:
    assert f'href="{slug}/"' in hub or f"href='{slug}/'" in hub, f"hub missing link: {slug}"

for path in pages:
    text = read(path)
    canonical = BASE if path.parent == SECTOR else BASE + path.parent.name + "/"
    checks = {
        "title": "<title>" in text.lower(),
        "description": bool(re.search(r'<meta\s+name=["\']description["\']', text, re.I)),
        "canonical": canonical in text and "canonical" in text.lower(),
        "robots": "max-video-preview:-1" in text,
        "og:title": "og:title" in text,
        "og:description": "og:description" in text,
        "og:url": "og:url" in text and canonical in text,
        "jsonld": "application/ld+json" in text,
    }
    failed = [k for k,v in checks.items() if not v]
    assert not failed, f"{path}: metadata failures {failed}"
    assert "warm-referral-continuity" not in text, f"legacy broken route in {path}"

for slug in ["community-help-project-methodology","synergetic-collaborative-family-model","physical-activity-quality-of-life-family-support","public-transport-social-inclusion-older-adults"]:
    assert FSD_SOURCE in read(SECTOR / slug / "index.html"), f"exact FSD source missing from {slug}"

xml_text = read(SITEMAP)
assert "warm-referral-continuity" not in xml_text, "broken legacy route remains in sitemap"
root = ET.fromstring(xml_text)
ns = {"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}
urls = [node.text.strip() for node in root.findall("s:url/s:loc", ns) if node.text]
assert len(urls) == 56, f"sitemap count={len(urls)}"
assert len(set(urls)) == 56, "duplicate sitemap URLs"
assert set(urls) == set(EXPECTED), f"sitemap mismatch missing={set(EXPECTED)-set(urls)} extra={set(urls)-set(EXPECTED)}"

print("SOCIAL_WORK_VALIDATION_OK pages=56 guides=55 sitemap=56")
