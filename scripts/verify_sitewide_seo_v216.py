#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
SCRIPT = ROOT / "scripts" / "enhance_sitewide_seo_v216.py"
JSONLD_BLOCK_RE = re.compile(
    r"<script\b[^>]*\btype\s*=\s*([\"'])application/ld\+json\1[^>]*>(.*?)</script\s*>",
    re.I | re.S,
)


def load_enhancer():
    spec = importlib.util.spec_from_file_location("enhance_sitewide_seo_v216", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load sitewide SEO enhancer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SITE = SITE
    return module


def page_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matching_tags(module, head: str, attribute: str, expected: str) -> list[dict[str, str]]:
    expected = expected.lower()
    found: list[dict[str, str]] = []
    for match in module.TAG_RE.finditer(head):
        parsed = module.attrs(match.group(0))
        if parsed.get(attribute, "").lower() == expected:
            found.append(parsed)
    return found


def main() -> int:
    if not SITE.is_dir():
        raise SystemExit(f"Missing production output: {SITE}")
    module = load_enhancer()
    report_path = SITE / "api" / "sitewide-seo-v216.json"
    if not report_path.is_file():
        raise SystemExit("Missing sitewide SEO production report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("version") != 216 or report.get("failure_count") != 0:
        raise SystemExit("Invalid or failed SEO enrichment report")
    if not (SITE / "assets" / "brand" / "social-card.svg").is_file():
        raise SystemExit("Missing social sharing image in production output")

    pages = sorted(SITE.rglob("*.html"))
    before = {path: page_hash(path) for path in pages}
    idempotency_failures: list[str] = []
    for path in pages:
        relative = path.relative_to(SITE).as_posix()
        if relative in module.SKIP_FILES or relative.startswith(module.SKIP_PREFIXES):
            continue
        changed, result = module.enrich_page(path)
        if changed:
            idempotency_failures.append(relative)
        if result.get("status") in {"missing_head", "missing_title_and_h1"}:
            idempotency_failures.append(relative)
    after = {path: page_hash(path) for path in pages}
    for path in pages:
        if before[path] != after[path] and path.relative_to(SITE).as_posix() not in idempotency_failures:
            idempotency_failures.append(path.relative_to(SITE).as_posix())

    failures: list[dict[str, str]] = []
    totals: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    routes: Counter[str] = Counter()
    for path in pages:
        relative = path.relative_to(SITE).as_posix()
        source = path.read_text(encoding="utf-8")
        totals["html_pages"] += 1
        if relative in module.SKIP_FILES or relative.startswith(module.SKIP_PREFIXES):
            totals["skipped_special"] += 1
            continue
        head_match = module.HEAD_RE.search(source)
        if not head_match:
            failures.append({"path": relative, "error": "missing head"})
            continue
        head = head_match.group(1)
        robots_tags = matching_tags(module, head, "name", "robots")
        robots = robots_tags[0].get("content", "") if robots_tags else ""
        if "noindex" in robots.lower():
            totals["skipped_noindex"] += 1
            continue

        totals["indexed_pages"] += 1
        language = module.language_of(source)
        languages[language] += 1
        routes[module.route_key(relative)] += 1

        title_matches = module.TITLE_RE.findall(head)
        if len(title_matches) != 1 or not module.clean_text(title_matches[0]):
            failures.append({"path": relative, "error": "title must exist exactly once"})

        singleton_meta = {
            ("name", "description"),
            ("name", "robots"),
            ("name", "keywords"),
            ("property", "og:type"),
            ("property", "og:site_name"),
            ("property", "og:locale"),
            ("property", "og:title"),
            ("property", "og:description"),
            ("property", "og:url"),
            ("property", "og:image"),
            ("property", "og:image:alt"),
            ("name", "twitter:card"),
            ("name", "twitter:title"),
            ("name", "twitter:description"),
            ("name", "twitter:image"),
            ("name", "twitter:image:alt"),
        }
        for attribute, expected in singleton_meta:
            tags = matching_tags(module, head, attribute, expected)
            if len(tags) != 1:
                failures.append(
                    {
                        "path": relative,
                        "error": f"{expected} count is {len(tags)}, expected 1",
                    }
                )
                continue
            if not tags[0].get("content", "").strip():
                failures.append({"path": relative, "error": f"{expected} is empty"})

        canonical_tags = matching_tags(module, head, "rel", "canonical")
        if len(canonical_tags) != 1:
            failures.append(
                {
                    "path": relative,
                    "error": f"canonical count is {len(canonical_tags)}, expected 1",
                }
            )
        else:
            canonical = canonical_tags[0].get("href", "")
            if not canonical.startswith(module.BASE_URL):
                failures.append({"path": relative, "error": "canonical outside platform scope"})

        keyword_tags = matching_tags(module, head, "name", "keywords")
        if len(keyword_tags) == 1:
            keyword_value = keyword_tags[0].get("content", "")
            keywords = [
                module.clean_text(item)
                for item in re.split(r"[,،]", keyword_value)
                if module.clean_text(item)
            ]
            normalized = [module.normalized_keyword(item) for item in keywords]
            if not 5 <= len(keywords) <= 15:
                failures.append(
                    {
                        "path": relative,
                        "error": f"keyword count {len(keywords)} outside 5..15",
                    }
                )
            if len(keyword_value) > 480:
                failures.append({"path": relative, "error": "keyword metadata exceeds 480 characters"})
            if len(normalized) != len(set(normalized)):
                failures.append({"path": relative, "error": "duplicate topical keywords"})

        if module.is_article(relative):
            article_tags = matching_tags(module, head, "property", "article:tag")
            unique_article_tags = {
                module.normalized_keyword(tag.get("content", ""))
                for tag in article_tags
                if tag.get("content", "").strip()
            }
            if len(unique_article_tags) < 5:
                failures.append({"path": relative, "error": "fewer than five article tags"})

        jsonld_blocks = [match[1] for match in JSONLD_BLOCK_RE.findall(head)]
        if not jsonld_blocks:
            failures.append({"path": relative, "error": "missing JSON-LD"})
        for block in jsonld_blocks:
            try:
                json.loads(block.replace("<\\/", "</"))
            except json.JSONDecodeError as exc:
                failures.append({"path": relative, "error": f"invalid JSON-LD: {exc}"})
                break

    if totals["indexed_pages"] < 2000:
        failures.append(
            {
                "path": "*",
                "error": f"only {totals['indexed_pages']} indexed pages were verified",
            }
        )
    if idempotency_failures:
        failures.append(
            {
                "path": "*",
                "error": f"SEO publisher is not idempotent for {len(set(idempotency_failures))} pages",
            }
        )

    verification = {
        "version": 216,
        "status": "passed" if not failures else "failed",
        "totals": dict(sorted(totals.items())),
        "languages": dict(sorted(languages.items())),
        "routes": dict(sorted(routes.items())),
        "idempotency_failure_count": len(set(idempotency_failures)),
        "idempotency_failures": sorted(set(idempotency_failures))[:300],
        "failure_count": len(failures),
        "failures": failures[:300],
    }
    output = SITE / "api" / "sitewide-seo-verification-v216.json"
    output.write_text(
        json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(f"Sitewide SEO verification failed: {len(failures)} issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
