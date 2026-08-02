#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v322" / "special-needs-condition-expansion-ar.parts"
BASE = "https://healthrenewal.org"
BP = "/"
VERSION = 322
MARKER_START = "<!-- special-needs-expansion-v322:start -->"
MARKER_END = "<!-- special-needs-expansion-v322:end -->"
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")
TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
FORBIDDEN_RUNTIME = ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "WebSocket(", "eval(", "new Function(")
EXPECTED_SLUGS = {
    "adhd-lifespan-assessment-support",
    "cerebral-palsy-lifespan-care-participation",
    "hearing-loss-deafness-language-access",
    "vision-impairment-learning-mobility-access",
    "developmental-language-disorder-assessment-support",
}


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        if path.is_dir():
            parts = sorted(path.glob("part-*.txt"))
            if not parts:
                raise ValueError(f"No content parts in {path}")
            encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
            compressed = base64.b64decode(encoded, validate=True)
            raw = gzip.decompress(compressed).decode("utf-8")
        else:
            raw = gzip.decompress(path.read_bytes()).decode("utf-8") if path.suffix == ".gz" else path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object required: {path}")
    return data


def is_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def visible_words(markup: str) -> int:
    return len(WORD_RE.findall(html.unescape(TAG_RE.sub(" ", markup))))


def validate_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("version") != VERSION or payload.get("language") != "ar":
        raise SystemExit("v322 content contract failed")
    if payload.get("review_status") != "internally-reviewed-external-clinical-review-required":
        raise SystemExit("v322 review status must remain honest")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(payload.get("reviewed_at", ""))):
        raise SystemExit("v322 reviewed_at must be an ISO date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(payload.get("next_review_due", ""))):
        raise SystemExit("v322 next_review_due must be an ISO date")

    guides = payload.get("guides")
    if not isinstance(guides, list) or len(guides) != 5:
        raise SystemExit("v322 must publish exactly five guides")
    slugs = {guide.get("slug") for guide in guides}
    if slugs != EXPECTED_SLUGS:
        raise SystemExit(f"Unexpected v322 routes: {sorted(str(item) for item in slugs)}")

    for guide in guides:
        serialized = json.dumps(guide, ensure_ascii=False)
        if BANNED.search(serialized):
            raise SystemExit(f"Banned terminology in {guide.get('slug')}")
        for key in (
            "slug", "related_path_slug", "category", "title", "short_title",
            "meta_description", "lead", "warning",
        ):
            if not str(guide.get(key, "")).strip():
                raise SystemExit(f"Missing {key}: {guide.get('slug')}")
        if len(guide.get("audiences", [])) < 4:
            raise SystemExit(f"Audience depth failed: {guide.get('slug')}")
        sections = guide.get("sections")
        if not isinstance(sections, list) or len(sections) != 8:
            raise SystemExit(f"Each v322 guide must contain eight sections: {guide.get('slug')}")
        if len(guide.get("action_steps", [])) < 6 or len(guide.get("urgent", [])) < 3:
            raise SystemExit(f"Action or urgent depth failed: {guide.get('slug')}")

        sources = guide.get("sources")
        if not isinstance(sources, list) or len(sources) < 4:
            raise SystemExit(f"Source depth failed: {guide.get('slug')}")
        source_index: dict[str, dict[str, Any]] = {}
        source_urls: set[str] = set()
        for source in sources:
            sid = str(source.get("id", "")).strip()
            url = str(source.get("url", "")).strip()
            if not sid or sid in source_index:
                raise SystemExit(f"Duplicate or empty source id: {guide.get('slug')}/{sid}")
            if not is_https(url) or url in source_urls:
                raise SystemExit(f"Invalid or duplicate source URL: {guide.get('slug')}/{url}")
            if source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
                raise SystemExit(f"Invalid source level: {guide.get('slug')}/{sid}")
            if not all(str(source.get(key, "")).strip() for key in ("organization", "title", "reviewed")):
                raise SystemExit(f"Incomplete source: {guide.get('slug')}/{sid}")
            source_index[sid] = source
            source_urls.add(url)

        section_ids: set[str] = set()
        used_sources: set[str] = set()
        for section in sections:
            section_id = str(section.get("id", "")).strip()
            if not section_id or section_id in section_ids:
                raise SystemExit(f"Invalid section id: {guide.get('slug')}/{section_id}")
            paragraphs = section.get("paragraphs")
            checkpoints = section.get("checkpoints")
            refs = section.get("source_ids")
            if not isinstance(paragraphs, list) or len(paragraphs) < 2:
                raise SystemExit(f"Paragraph depth failed: {guide.get('slug')}/{section_id}")
            if min((len(WORD_RE.findall(str(item))) for item in paragraphs), default=0) < 45:
                raise SystemExit(f"Paragraph too short: {guide.get('slug')}/{section_id}")
            if not isinstance(checkpoints, list) or len(checkpoints) < 4:
                raise SystemExit(f"Checkpoint depth failed: {guide.get('slug')}/{section_id}")
            if not isinstance(refs, list) or not refs or any(ref not in source_index for ref in refs):
                raise SystemExit(f"Section evidence failed: {guide.get('slug')}/{section_id}")
            section_ids.add(section_id)
            used_sources.update(refs)
        unused = sorted(set(source_index) - used_sources)
        if unused:
            raise SystemExit(f"Unused sources: {guide.get('slug')}/{unused}")
    return guides


CSS = """
:root{--ink:#123f43;--muted:#4f6e71;--brand:#075f5b;--brand2:#08776e;--accent:#823353;--line:#c6e1de;--mint:#effbf8;--pink:#fff2f6;--white:#fff;--shadow:0 14px 36px rgba(18,63,67,.10)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:var(--ink);background:linear-gradient(145deg,#fff,var(--mint));line-height:1.95}
a{color:#056b65}.wrap{width:min(1160px,92%);margin:auto}.skip{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px 14px;border:2px solid var(--brand);z-index:90}.skip:focus{right:8px}
header{background:#123f43;color:#fff}.head{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:12px 0}.head a{color:#fff;text-decoration:none;font-weight:900}.head nav{display:flex;gap:12px;flex-wrap:wrap}
.hero{padding:58px 0 32px;background:linear-gradient(135deg,#e7f8f4,#fff,#fff1f6)}.eyebrow{font-weight:900;color:var(--accent)}h1{font-size:clamp(2.15rem,5vw,4.25rem);line-height:1.2;margin:.2em 0}h2{font-size:clamp(1.35rem,3vw,2rem);line-height:1.4}.lead{font-size:1.12rem;color:var(--muted)}
.notice,.section-card,.panel,.sources{background:rgba(255,255,255,.98);border:1px solid var(--line);border-radius:20px;padding:21px;box-shadow:var(--shadow)}.notice{border-right:6px solid var(--accent)}.grid{display:grid;grid-template-columns:270px 1fr;gap:22px;padding:32px 0}.toc{position:sticky;top:16px;align-self:start}.toc a{display:block;padding:7px 0;border-bottom:1px solid #e2efed;text-decoration:none}.stack{display:grid;gap:18px}.kicker{font-weight:900;color:var(--accent)}.checkpoints{background:#f3fbf9;border-radius:14px;padding:12px 18px}.refs{font-size:.95rem}.urgent{border-right:6px solid #a32727;background:#fff5f5}.actions{border-right:6px solid var(--brand2)}.sources li{margin:1rem 0}.level{display:inline-block;background:#e4f6f2;border-radius:8px;padding:1px 7px;font-weight:900}.button{display:inline-block;background:#b8eee5;color:#123f43;text-decoration:none;font-weight:900;padding:10px 14px;border-radius:12px;margin:4px}.review{background:#fff8e9;border:1px solid #e6cf9f;border-radius:14px;padding:12px}
footer{margin-top:32px;padding:28px 0;border-top:1px solid var(--line);color:var(--muted)}a:focus-visible,summary:focus-visible{outline:3px solid #0a8179;outline-offset:4px}
@media(max-width:820px){.head,.grid{display:block}.head nav{margin-top:10px}.toc{position:static;margin-bottom:18px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{header,.skip,.toc{display:none}.grid{display:block}.section-card,.panel,.sources{box-shadow:none}}
"""


def page_schema(guide: dict[str, Any], payload: dict[str, Any]) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    related = f"{BASE}/special-needs/{guide['related_path_slug']}/"
    graph = [
        {
            "@type": "MedicalWebPage",
            "@id": url + "#page",
            "url": url,
            "name": guide["title"],
            "description": guide["meta_description"],
            "inLanguage": "ar",
            "dateModified": payload["reviewed_at"],
            "audience": [{"@type": "Audience", "audienceType": item} for item in guide["audiences"]],
            "isPartOf": {"@id": f"{BASE}/special-needs/#page"},
            "relatedLink": related,
            "about": {"@type": "MedicalCondition", "name": guide["short_title"]},
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": BASE + "/special-needs/"},
                {"@type": "ListItem", "position": 3, "name": guide["short_title"], "item": url},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")
