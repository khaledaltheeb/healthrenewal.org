#!/usr/bin/env python3
"""Apply hand-authored Quick Info overlays to the recovered production artifact.

No article prose is generated here. Each reviewed HTML fragment is committed under
content/quick-info-editorial/<batch>. The script preserves the recovered article,
replaces only its old generic source box, adds the reviewed expansion, refreshes
modification metadata, normalizes runtime, links the upgraded pages from the hub,
and fails closed on thin or overly similar editorial output.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

EXPECTED_PRIMARY = 250
DEFAULT_MIN_TOTAL_WORDS = 1500
MAX_BATCH_COSINE = 0.20
GA_ID = "G-VLZMV8Y4JP"
MODIFIED_DATE = "2026-08-08"
MODIFIED_ISO = "2026-08-08T17:00:00+03:00"

TAG_RE = re.compile(r"<[^>]+>", re.S)
SCRIPT_RE = re.compile(r"<(?:script|style|noscript)\b.*?</(?:script|style|noscript)>", re.I | re.S)
WORD_RE = re.compile(r"[A-Za-z0-9_\u0600-\u06FF]+", re.UNICODE)
MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.I | re.S)
HEAD_OPEN_RE = re.compile(r"<head\b[^>]*>", re.I)
SOURCE_RE = re.compile(
    r"<section\b(?=[^>]*class=[\"'][^\"']*article-section[^\"']*sources[^\"']*[\"'])[^>]*>.*?</section>",
    re.I | re.S,
)
ARTICLE_MOD_RE = re.compile(r"<meta\b[^>]*property=[\"']article:modified_time[\"'][^>]*>", re.I)
JSON_MOD_RE = re.compile(r'"dateModified"\s*:\s*"\d{4}-\d{2}-\d{2}"')
VISIBLE_UPDATE_RE = re.compile(r"(<span\b[^>]*class=[\"'][^\"']*pill[^\"']*[\"'][^>]*>تحديث:)[^<]*(</span>)")

GA_SNIPPET = f'''<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>'''

GOVERNANCE_SECTION = '''<section class="article-section sources editorial-governance">
<h2>منهجية التحرير والمراجعة</h2>
<p>حُدّثت هذه الصفحة بعد قراءة نسختها السابقة والحفاظ على معلوماتها المفيدة، ثم أضيفت مراجعة موضوعية مخصصة. راجع <a href="/editorial-methodology/">المنهجية التحريرية</a> و<a href="/trust/">منهجية الثقة والمصادر</a> لمعرفة ضوابط المراجعة وحدود المحتوى التثقيفي.</p>
</section>'''


def clean_text(fragment: str) -> str:
    fragment = SCRIPT_RE.sub(" ", fragment)
    fragment = TAG_RE.sub(" ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def word_count(fragment: str) -> int:
    return len(WORD_RE.findall(clean_text(fragment)))


def main_word_count(source: str) -> int:
    match = MAIN_RE.search(source)
    return word_count(match.group(1) if match else source)


def external_links(fragment: str) -> list[str]:
    return sorted(set(re.findall(r'href=[\"\'](https?://[^\"\']+)', fragment, re.I)))


def markers(batch: str) -> tuple[str, str]:
    return (
        f"<!-- QUICK_INFO_EDITORIAL_BATCH_{batch}_START -->",
        f"<!-- QUICK_INFO_EDITORIAL_BATCH_{batch}_END -->",
    )


def strip_batch(source: str, batch: str) -> str:
    start, end = markers(batch)
    return re.sub(re.escape(start) + r".*?" + re.escape(end), "", source, flags=re.S)


def add_ga(source: str) -> str:
    if GA_ID in source:
        return source
    match = HEAD_OPEN_RE.search(source)
    if not match:
        raise ValueError("missing <head>")
    return source[: match.end()] + "\n" + GA_SNIPPET + "\n" + source[match.end() :]


def update_modified_metadata(source: str) -> str:
    meta = f'<meta property="article:modified_time" content="{MODIFIED_ISO}">'
    source = ARTICLE_MOD_RE.sub(meta, source, count=1) if ARTICLE_MOD_RE.search(source) else source.replace("</head>", meta + "\n</head>", 1)
    source = JSON_MOD_RE.sub(f'"dateModified":"{MODIFIED_DATE}"', source, count=1)
    source = VISIBLE_UPDATE_RE.sub(r"\g<1> 8 أغسطس 2026\g<2>", source, count=1)
    return source


def apply_overlay(source: str, overlay: str, batch: str) -> str:
    source = strip_batch(source, batch)
    start, end = markers(batch)
    block = f"{start}\n{overlay.strip()}\n{GOVERNANCE_SECTION}\n{end}"
    source_match = SOURCE_RE.search(source)
    if source_match:
        return source[: source_match.start()] + block + source[source_match.end() :]
    for fallback in ('<aside class="side">', "</article>", "</main>"):
        position = source.find(fallback)
        if position >= 0:
            return source[:position] + block + "\n" + source[position:]
    raise ValueError("unable to locate editorial insertion point")


def tokens_without_headings(fragment: str) -> list[str]:
    fragment = re.sub(r"<h[1-6]\b[^>]*>.*?</h[1-6]>", " ", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<summary\b[^>]*>.*?</summary>", " ", fragment, flags=re.I | re.S)
    return [token.lower() for token in WORD_RE.findall(clean_text(fragment))]


def bigrams(fragment: str) -> Counter[tuple[str, str]]:
    tokens = tokens_without_headings(fragment)
    return Counter(zip(tokens, tokens[1:]))


def cosine(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0
    dot = sum(left[key] * right[key] for key in set(left) & set(right))
    ln = math.sqrt(sum(value * value for value in left.values()))
    rn = math.sqrt(sum(value * value for value in right.values()))
    return dot / (ln * rn) if ln and rn else 0.0


def similarity_report(overlays: dict[str, str]) -> tuple[float, list[dict[str, object]]]:
    vectors = {slug: bigrams(fragment) for slug, fragment in overlays.items()}
    slugs = sorted(vectors)
    pairs: list[dict[str, object]] = []
    maximum = 0.0
    for index, left in enumerate(slugs):
        for right in slugs[index + 1 :]:
            score = cosine(vectors[left], vectors[right])
            maximum = max(maximum, score)
            pairs.append({"left": left, "right": right, "cosine": round(score, 4)})
    pairs.sort(key=lambda item: item["cosine"], reverse=True)
    return maximum, pairs


def repeated_paragraphs(overlays: dict[str, str]) -> list[dict[str, object]]:
    owners: dict[str, set[str]] = defaultdict(set)
    for slug, fragment in overlays.items():
        for paragraph in re.findall(r"<p\b[^>]*>(.*?)</p>", fragment, re.I | re.S):
            normalized = clean_text(paragraph)
            if word_count(normalized) >= 20:
                owners[normalized].add(slug)
    return [
        {"paragraph": paragraph, "slugs": sorted(slugs)}
        for paragraph, slugs in owners.items()
        if len(slugs) > 1
    ]


def update_hub(root: Path, batch: str, items: list[dict[str, object]]) -> None:
    path = root / "quick-info" / "index.html"
    source = path.read_text(encoding="utf-8")
    start = f"<!-- QUICK_INFO_EDITORIAL_DIRECTORY_{batch}_START -->"
    end = f"<!-- QUICK_INFO_EDITORIAL_DIRECTORY_{batch}_END -->"
    source = re.sub(re.escape(start) + r".*?" + re.escape(end), "", source, flags=re.S)
    cards = "".join(
        f'<a class="card" href="/quick-info/{html.escape(str(item["slug"]))}/"><h3>{html.escape(str(item["title"]))}</h3><p>نسخة تاريخية أعيدت قراءتها وتوسيعها وتدقيق مصادرها ضمن الدفعة التحريرية {batch}.</p></a>'
        for item in items
    )
    block = (
        f'{start}<section class="wrap recovered-directory editorial-reviewed-directory">'
        f'<p class="eyebrow">محتوى تاريخي تمت ترقيته</p><h2>دفعة تحريرية مراجعة: {len(items)} صفحات</h2>'
        '<p>هذه الصفحات لم تُوسّع بقالب آلي؛ قُرئت نسخها القديمة ثم أضيف محتوى مخصص ومراجع مرتبطة بالموضوع.</p>'
        f'<div class="grid">{cards}</div></section>{end}'
    )
    position = source.lower().rfind("</main>")
    if position < 0:
        raise ValueError("Quick Info hub has no </main>")
    path.write_text(source[:position] + block + "\n" + source[position:], encoding="utf-8", newline="\n")


def update_section_sitemap(root: Path, slugs: list[str]) -> int:
    path = root / "sitemap-quick-info.xml"
    source = path.read_text(encoding="utf-8")
    additions: list[str] = []
    for slug in slugs:
        url = f"https://healthrenewal.org/quick-info/{slug}/"
        if f"<loc>{url}</loc>" not in source:
            additions.append(f"<url><loc>{xml_escape(url)}</loc><lastmod>{MODIFIED_DATE}</lastmod></url>")
    if additions:
        source = source.replace("</urlset>", "\n" + "\n".join(additions) + "\n</urlset>", 1)
        path.write_text(source, encoding="utf-8", newline="\n")
    return source.count("<url>")


def normalize_runtime(root: Path, repo_root: Path) -> dict[str, int]:
    sys.path.insert(0, str(repo_root / "scripts"))
    import inject_google_tag_manager as gtm  # type: ignore
    import normalize_platform_shell as shell  # type: ignore

    shell.copy_platform_runtime(root)
    pages = [root / "quick-info" / "index.html"] + sorted((root / "quick-info").glob("*/index.html"))
    changed_shell = changed_gtm = changed_ga = 0
    failures: list[str] = []
    for page in pages:
        result = shell.normalize_file(page, root, check_only=False)
        changed_shell += int(result.status == "updated")
        if result.status in {"error", "skipped"}:
            failures.append(f"{result.path}: {result.status} {result.detail}")
        source = page.read_text(encoding="utf-8")
        with_ga = add_ga(source)
        if with_ga != source:
            changed_ga += 1
            page.write_text(with_ga, encoding="utf-8", newline="\n")
        changed, warnings = gtm.patch_html(page)
        changed_gtm += int(changed)
        failures.extend(f"{page.relative_to(root)}: {warning}" for warning in warnings)
        final = page.read_text(encoding="utf-8-sig")
        if GA_ID not in final or gtm.GTM_ID not in final or "pt-platform-shell:v1" not in final:
            failures.append(f"{page.relative_to(root)}: runtime contract incomplete")
    if failures:
        raise ValueError("; ".join(failures[:20]))
    return {"pages": len(pages), "shellUpdated": changed_shell, "gtmUpdated": changed_gtm, "gaUpdated": changed_ga}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--batch", default="001")
    parser.add_argument("--minimum-total-words", type=int, default=DEFAULT_MIN_TOTAL_WORDS)
    args = parser.parse_args()

    root = args.root.resolve()
    repo_root = args.repo_root.resolve()
    batch_dir = repo_root / "content" / "quick-info-editorial" / args.batch
    fragments = sorted(batch_dir.glob("*.html"))
    if not fragments:
        raise SystemExit(f"No editorial fragments found in {batch_dir}")

    payload = json.loads((root / "api" / "v1" / "quick-info.json").read_text(encoding="utf-8"))
    primary_slugs = {str(item["slug"]) for item in payload.get("items", [])}
    if payload.get("count") != EXPECTED_PRIMARY or len(primary_slugs) != EXPECTED_PRIMARY:
        raise SystemExit("Primary Quick Info inventory is not the expected 250 pages")

    overlays = {fragment.stem: fragment.read_text(encoding="utf-8") for fragment in fragments}
    maximum_similarity, similarity_pairs = similarity_report(overlays)
    repeats = repeated_paragraphs(overlays)
    failures: list[str] = []
    if maximum_similarity > MAX_BATCH_COSINE:
        failures.append(f"batch cosine similarity {maximum_similarity:.4f} > {MAX_BATCH_COSINE}")
    if repeats:
        failures.append(f"{len(repeats)} long paragraphs repeat across batch pages")

    results: list[dict[str, object]] = []
    for slug, overlay in overlays.items():
        page = root / "quick-info" / slug / "index.html"
        if not page.is_file():
            failures.append(f"missing recovered page: {slug}")
            continue
        reviewed_sources = external_links(overlay)
        if len(reviewed_sources) < 3:
            failures.append(f"{slug}: fewer than 3 reviewed external sources")
            continue
        source = apply_overlay(page.read_text(encoding="utf-8"), overlay, args.batch)
        source = update_modified_metadata(source)
        page.write_text(source, encoding="utf-8", newline="\n")
        final_words = main_word_count(source)
        start, _ = markers(args.batch)
        if final_words < args.minimum_total_words:
            failures.append(f"{slug}: {final_words} words < {args.minimum_total_words}")
        if source.count(start) != 1:
            failures.append(f"{slug}: editorial marker count is {source.count(start)}")
        title_match = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)
        results.append({
            "slug": slug,
            "title": clean_text(title_match.group(1)) if title_match else slug,
            "url": f"https://healthrenewal.org/quick-info/{slug}/",
            "origin": "primary" if slug in primary_slugs else "historical-recovered",
            "totalWords": final_words,
            "overlayWords": word_count(overlay),
            "reviewedSources": reviewed_sources,
        })

    update_hub(root, args.batch, results)
    sitemap_urls = update_section_sitemap(root, [str(item["slug"]) for item in results])
    runtime = normalize_runtime(root, repo_root)

    actual_pages = sorted((root / "quick-info").glob("*/index.html"))
    recovered_total = sum(page.parent.name not in primary_slugs for page in actual_pages)
    upgraded_recovered = sum(item["origin"] == "historical-recovered" for item in results)
    backlog = recovered_total - upgraded_recovered
    report = {
        "version": "1.0.0",
        "batch": args.batch,
        "status": "passed" if not failures else "failed",
        "primaryInventory": len(primary_slugs),
        "productionArticlePages": len(actual_pages),
        "historicalRecoveredPages": recovered_total,
        "batchPages": len(results),
        "historicalRecoveredUpgraded": upgraded_recovered,
        "historicalRecoveredBacklog": backlog,
        "minimumTotalWordsRequired": args.minimum_total_words,
        "minimumBatchTotalWords": min((int(item["totalWords"]) for item in results), default=0),
        "maximumBatchContentCosine": round(maximum_similarity, 4),
        "maximumAllowedBatchCosine": MAX_BATCH_COSINE,
        "repeatedLongParagraphs": len(repeats),
        "sectionSitemapUrls": sitemap_urls,
        "runtime": runtime,
        "similarityPairs": similarity_pairs,
        "failures": failures,
        "items": results,
    }
    report_path = root / "api" / f"quick-info-editorial-batch-{args.batch}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"items", "similarityPairs"}}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit("\n".join(failures[:30]))


if __name__ == "__main__":
    main()
