from __future__ import annotations

import html
import json
import re
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "care-guides/clinical-literacy"
SLUGS = [
    "adhd-screening-vs-diagnosis",
    "adult-adhd-assessment",
    "child-adhd-assessment-home-school",
    "adhd-rating-scales-guide",
]
MIN_WORDS = 1500
MIN_SOURCES = 3
MIN_INTERNAL_LINKS = 6
MAX_PARAGRAPH_JACCARD = 0.35
MAX_SHARED_LONG_PARAGRAPH_RATIO = 0.20


def strip_html(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def words(text: str) -> list[str]:
    return re.findall(r"[\w\u0600-\u06ff]+", strip_html(text), flags=re.UNICODE)


def paragraphs(text: str) -> list[str]:
    out = []
    for raw in re.findall(r"<p\b[^>]*>(.*?)</p>", text, flags=re.I | re.S):
        value = strip_html(raw).lower()
        value = re.sub(r"\s+", " ", value).strip()
        if len(value.split()) >= 40:
            out.append(value)
    return out


def paragraph_jaccard(left: str, right: str) -> float:
    a, b = set(paragraphs(left)), set(paragraphs(right))
    return len(a & b) / len(a | b) if a and b else 0.0


def title(text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", text, flags=re.I | re.S)
    return strip_html(match.group(1)) if match else ""


def meta(text: str) -> str:
    match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', text, flags=re.I)
    return html.unescape(match.group(1)).strip() if match else ""


def canonical(text: str) -> str:
    match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', text, flags=re.I)
    return match.group(1).strip() if match else ""


def main() -> int:
    errors: list[str] = []
    records: dict[str, dict[str, object]] = {}
    texts: dict[str, str] = {}

    for slug in SLUGS:
        path = BASE / slug / "index.html"
        if not path.exists():
            errors.append(f"missing page: {slug}")
            continue
        text = path.read_text(encoding="utf-8")
        texts[slug] = text
        wc = len(words(text))
        source_links = set(re.findall(r'href="https?://([^/\"]+)[^\"]*"', text, flags=re.I))
        internal_links = set(re.findall(r'href="(/[^\"]+)"', text, flags=re.I))
        record = {
            "words": wc,
            "sourceHosts": sorted(source_links),
            "internalLinks": len(internal_links),
            "title": title(text),
            "meta": meta(text),
            "canonical": canonical(text),
            "longParagraphs": len(paragraphs(text)),
        }
        records[slug] = record
        if wc < MIN_WORDS:
            errors.append(f"{slug}: thin page {wc} < {MIN_WORDS}")
        if len(source_links) < MIN_SOURCES:
            errors.append(f"{slug}: source hosts {len(source_links)} < {MIN_SOURCES}")
        if len(internal_links) < MIN_INTERNAL_LINKS:
            errors.append(f"{slug}: internal links {len(internal_links)} < {MIN_INTERNAL_LINKS}")
        if not record["title"] or not record["meta"] or not record["canonical"]:
            errors.append(f"{slug}: missing title/meta/canonical")
        if "application/ld+json" not in text or "BreadcrumbList" not in text:
            errors.append(f"{slug}: missing structured data/breadcrumb")
        if "لا يقدم تشخيص" not in text and "لا تستبدل" not in text and "لا تفسر درجة فردية" not in text:
            errors.append(f"{slug}: missing explicit non-diagnostic boundary")

    if len({r["title"] for r in records.values()}) != len(records):
        errors.append("duplicate titles")
    if len({r["meta"] for r in records.values()}) != len(records):
        errors.append("duplicate meta descriptions")
    if len({r["canonical"] for r in records.values()}) != len(records):
        errors.append("duplicate canonicals")

    pairwise = []
    all_long: dict[str, set[str]] = {slug: set(paragraphs(text)) for slug, text in texts.items()}
    for left, right in combinations(SLUGS, 2):
        if left not in texts or right not in texts:
            continue
        score = paragraph_jaccard(texts[left], texts[right])
        shared = all_long[left] & all_long[right]
        denom = min(len(all_long[left]), len(all_long[right])) or 1
        ratio = len(shared) / denom
        pairwise.append({"left": left, "right": right, "paragraphJaccard": round(score, 4), "sharedLongParagraphRatio": round(ratio, 4)})
        if score > MAX_PARAGRAPH_JACCARD:
            errors.append(f"{left} vs {right}: paragraph jaccard {score:.3f} > {MAX_PARAGRAPH_JACCARD}")
        if ratio > MAX_SHARED_LONG_PARAGRAPH_RATIO:
            errors.append(f"{left} vs {right}: shared long paragraph ratio {ratio:.3f} > {MAX_SHARED_LONG_PARAGRAPH_RATIO}")

    report = {
        "schemaVersion": 1,
        "wave": "002A",
        "requiredPages": len(SLUGS),
        "validatedPages": len(records),
        "minimumWords": min((r["words"] for r in records.values()), default=0),
        "minimumInternalLinks": min((r["internalLinks"] for r in records.values()), default=0),
        "records": records,
        "pairwise": pairwise,
        "errors": errors,
        "status": "passed" if not errors and len(records) == len(SLUGS) else "failed",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
