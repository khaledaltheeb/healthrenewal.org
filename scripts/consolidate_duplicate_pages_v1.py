#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

BASE = "https://healthrenewal.org"
MARKER = "duplicate-consolidation-v1"

# Confirmed duplicate routes from the validated production artifact. Audience-
# specific family/provider guides are intentionally excluded unless their text
# and purpose are substantially identical. Cross-surface aliases may still be
# canonicalized without copying route-relative fragments into the public page.
DUPLICATE_GROUPS = (
    {"target": "terms/cognitive-psychology/index.html", "aliases": ("library/branches/cognitive-psychology/index.html",)},
    {"target": "terms/educational-psychology/index.html", "aliases": ("library/branches/educational-psychology/index.html",)},
    {"target": "terms/social-psychology/index.html", "aliases": ("library/branches/social-psychology/index.html",)},
    {"target": "terms/industrial-organizational-psychology/index.html", "aliases": ("library/branches/industrial-organizational-psychology/index.html",)},
    {"target": "terms/positive-psychology/index.html", "aliases": ("library/branches/positive-psychology/index.html",)},
    {"target": "terms/developmental-psychology/index.html", "aliases": ("library/branches/developmental-psychology/index.html",)},
    {"target": "terms/dialectical-behavior-therapy/index.html", "aliases": ("library/therapies/dialectical-behavior-therapy/index.html",)},
    {"target": "terms/family-therapy/index.html", "aliases": ("library/therapies/family-therapy/index.html",)},
    {"target": "terms/cognitive-behavioral-therapy/index.html", "aliases": ("library/therapies/cognitive-behavioral-therapy/index.html",)},
    {"target": "terms/acceptance-and-commitment-therapy/index.html", "aliases": ("library/therapies/acceptance-commitment-therapy/index.html",)},
    {"target": "terms/psychoeducation/index.html", "aliases": ("library/therapies/psychoeducation/index.html",)},
    {"target": "terms/behavioral-activation/index.html", "aliases": ("library/therapies/behavioral-activation/index.html",)},
    {
        "target": "special-needs/conditions/global-developmental-delay/index.html",
        "aliases": ("provider-assessment-demo/conditions/global-developmental-delay/index.html",),
        "mergeFragments": False,
    },
)

TAG_RE = re.compile(r"<[^>]+>", re.S)
SPACE_RE = re.compile(r"\s+")
FRAGMENT_RE = re.compile(r"<(p|li)\b[^>]*>.*?</\1\s*>", re.I | re.S)
MAIN_END_RE = re.compile(r"</main\s*>", re.I)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title\s*>", re.I | re.S)
URL_BLOCK_RE = re.compile(r"<url>.*?</url>", re.I | re.S)
LOC_RE = re.compile(r"<loc>(.*?)</loc>", re.I | re.S)


def route(path: str) -> str:
    return re.sub(r"/+", "/", "/" + path.removesuffix("index.html"))


def absolute(path: str) -> str:
    return BASE + route(path)


def text_only(value: str) -> str:
    value = TAG_RE.sub(" ", value)
    value = html.unescape(value).lower().replace("ـ", "")
    value = re.sub(r"[\u064b-\u065f\u0670\u06d6-\u06ed]", "", value)
    value = re.sub(r"[^\w\u0600-\u06ff]+", " ", value)
    return SPACE_RE.sub(" ", value).strip()


def word_count(value: str) -> int:
    return len(text_only(value).split())


def fragments(source: str) -> list[dict[str, str | int]]:
    result = []
    for match in FRAGMENT_RE.finditer(source):
        block = match.group(0)
        normalized = text_only(block)
        words = len(normalized.split())
        if words < 10:
            continue
        if any(marker in normalized for marker in (
            "الرئيسية", "حقوق النشر", "آخر تحديث", "المراجعة التالية",
            "هذا المحتوى للتثقيف", "لا يغني عن",
        )):
            continue
        result.append({"html": block, "text": normalized, "words": words})
    return result


def unique_fragments(target_html: str, alias_html: str) -> list[str]:
    target_texts = [str(item["text"]) for item in fragments(target_html)]
    accepted: list[str] = []
    seen: set[str] = set()
    for item in fragments(alias_html):
        normalized = str(item["text"])
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        if normalized in target_texts:
            continue
        similarity = max(
            (SequenceMatcher(None, normalized, other).ratio() for other in target_texts),
            default=0.0,
        )
        if similarity >= 0.80:
            continue
        accepted.append(str(item["html"]))
    return accepted[:30]


def inject(target_html: str, alias_path: str, blocks: list[str]) -> str:
    if not blocks:
        return target_html
    source_route = route(alias_path)
    section_id = "merged-" + hashlib.sha1(alias_path.encode("utf-8")).hexdigest()[:10]
    merged = (
        f'\n<section class="merged-duplicate-content" data-source-route="{html.escape(source_route, quote=True)}" '
        f'aria-labelledby="{section_id}">\n'
        f'<h2 id="{section_id}">محتوى فريد مدمج من المسار السابق</h2>\n'
        + "\n".join(blocks)
        + "\n</section>\n"
    )
    matches = list(MAIN_END_RE.finditer(target_html))
    if matches:
        position = matches[-1].start()
        return target_html[:position] + merged + target_html[position:]
    return target_html + merged


def redirect_page(alias_path: str, target_path: str, previous_html: str) -> str:
    target_route = route(target_path)
    target_abs = absolute(target_path)
    title_match = TITLE_RE.search(previous_html)
    previous_title = text_only(title_match.group(1)) if title_match else "الصفحة"
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>انتقلت {html.escape(previous_title)} إلى الصفحة الموحدة</title>
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{html.escape(target_abs, quote=True)}">
<meta http-equiv="refresh" content="0; url={html.escape(target_route, quote=True)}">
</head>
<body>
<main id="main-content">
<h1>تم توحيد الصفحة</h1>
<p>دُمج المحتوى الفريد في الصفحة الأساسية لمنع التكرار وتحديث مرجع واحد.</p>
<p><a href="{html.escape(target_route, quote=True)}">الانتقال إلى الصفحة الموحدة</a></p>
</main>
<!-- {MARKER}; source={html.escape(route(alias_path), quote=True)}; target={html.escape(target_route, quote=True)} -->
</body>
</html>
'''


def rewrite_internal_links(site: Path, replacements: dict[str, str]) -> int:
    changed = 0
    variants: list[tuple[str, str]] = []
    for source_path, target_path in replacements.items():
        source_route, target_route = route(source_path), route(target_path)
        variants.extend(((BASE + source_route, BASE + target_route), (source_route, target_route)))
    for page in site.rglob("*.html"):
        source = page.read_text(encoding="utf-8", errors="replace")
        updated = source
        for old, new in variants:
            updated = updated.replace(old, new)
        if updated != source:
            page.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def dedupe_sitemap(source: str) -> str:
    seen: set[str] = set()
    output = source
    for block in URL_BLOCK_RE.findall(source):
        loc_match = LOC_RE.search(block)
        if not loc_match:
            continue
        loc = html.unescape(loc_match.group(1)).strip()
        if loc in seen:
            output = output.replace(block, "", 1)
        else:
            seen.add(loc)
    return output


def rewrite_sitemaps(site: Path, replacements: dict[str, str]) -> int:
    changed = 0
    variants = [(absolute(source), absolute(target)) for source, target in replacements.items()]
    for sitemap in site.glob("sitemap*.xml"):
        source = sitemap.read_text(encoding="utf-8", errors="replace")
        updated = source
        for old, new in variants:
            updated = updated.replace(old, new)
        updated = dedupe_sitemap(updated)
        if updated != source:
            sitemap.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def consolidate(site: Path, report: dict | None = None) -> dict:
    site = site.resolve()
    merged_groups: list[dict] = []
    consolidated: list[dict] = []
    merged_fragments: list[dict] = []
    replacements: dict[str, str] = {}

    for group in DUPLICATE_GROUPS:
        target_path = group["target"]
        target_file = site / target_path
        if not target_file.is_file():
            continue
        target_html = target_file.read_text(encoding="utf-8", errors="replace")
        merge_fragments = bool(group.get("mergeFragments", True))
        group_aliases: list[str] = []
        for alias_path in group["aliases"]:
            alias_file = site / alias_path
            if not alias_file.is_file():
                continue
            alias_html = alias_file.read_text(encoding="utf-8", errors="replace")
            if MARKER in alias_html and absolute(target_path) in alias_html:
                replacements[alias_path] = target_path
                group_aliases.append(alias_path)
                continue
            blocks = unique_fragments(target_html, alias_html) if merge_fragments else []
            if blocks:
                target_html = inject(target_html, alias_path, blocks)
                merged_fragments.append({"target": target_path, "source": alias_path, "fragments": len(blocks)})
            alias_file.write_text(redirect_page(alias_path, target_path, alias_html), encoding="utf-8")
            replacements[alias_path] = target_path
            group_aliases.append(alias_path)
            consolidated.append({
                "path": alias_path,
                "target": route(target_path),
                "previousWords": word_count(alias_html),
                "mergedUniqueFragments": len(blocks),
                "reason": (
                    "confirmed near-duplicate page consolidated into one canonical route"
                    if merge_fragments
                    else "cross-surface alias canonicalized without fragment transfer"
                ),
            })
        if group_aliases:
            target_file.write_text(target_html, encoding="utf-8")
            merged_groups.append({"target": target_path, "aliases": group_aliases})

    rewritten_pages = rewrite_internal_links(site, replacements)
    rewritten_sitemaps = rewrite_sitemaps(site, replacements)
    result = {
        "status": "passed",
        "version": 1,
        "duplicateRoutesConsolidated": len(replacements),
        "duplicateGroupsMerged": len(merged_groups),
        "mergedUniqueSections": sum(item["fragments"] for item in merged_fragments),
        "internalHtmlFilesRewritten": rewritten_pages,
        "sitemapsRewritten": rewritten_sitemaps,
        "consolidated": consolidated,
        "mergedSections": merged_fragments,
        "groups": merged_groups,
    }
    if report is None:
        report_path = site / "api" / "content-recovery-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    report.update({
        "duplicateRoutesConsolidated": result["duplicateRoutesConsolidated"],
        "duplicateGroupsMerged": result["duplicateGroupsMerged"],
        "consolidated": result["consolidated"],
        "mergedSections": result["mergedSections"],
        "duplicateConsolidationStatus": "passed",
    })
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "duplicate-consolidation-v1.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (api / "content-recovery-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="_site")
    args = parser.parse_args()
    print(json.dumps(consolidate(Path(args.site)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
