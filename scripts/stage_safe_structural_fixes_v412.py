#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any

VERSION = 412
BASE_URL = "https://healthrenewal.org/"
SKIP_PARTS = {".git", ".github", "node_modules", "vendor", "dist", "build", "_site", "artifacts", "reports", "tests", "test-results", "coverage", "__pycache__"}
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
LATIN_RE = re.compile(r"[A-Za-z]")
HTML_OPEN_RE = re.compile(r"<html\b([^>]*)>", re.I)
TITLE_RE = re.compile(r"<title\b[^>]*>.*?</title\s*>", re.I | re.S)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1\s*>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.I)
CANONICAL_RE = re.compile(r"<link\b(?=[^>]*\brel\s*=\s*([\"'])canonical\1)[^>]*>", re.I)
META_DESCRIPTION_RE = re.compile(r"<meta\b(?=[^>]*\bname\s*=\s*([\"'])description\1)[^>]*>", re.I)
OG_DESCRIPTION_RE = re.compile(r"<meta\b(?=[^>]*\bproperty\s*=\s*([\"'])og:description\1)[^>]*>", re.I)
CONTENT_RE = re.compile(r"\bcontent\s*=\s*([\"'])(.*?)\1", re.I | re.S)
ATTR_RE_TEMPLATE = r"\s+{name}\s*=\s*([\"']).*?\1"


def public_html(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*.html")):
        rel = path.relative_to(root)
        if path.name == "404.html" or any(part in SKIP_PARTS or part.startswith(".") for part in rel.parts):
            continue
        files.append(path)
    return files


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_manifest(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256_bytes(p.read_bytes()) for p in public_html(root)}


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", value)).strip()


def infer_lang(text: str) -> str | None:
    visible = strip_tags(re.sub(r"<(script|style|svg|template|noscript)\b.*?</\1\s*>", " ", text, flags=re.I | re.S))
    ar = len(ARABIC_RE.findall(visible))
    en = len(LATIN_RE.findall(visible))
    if ar >= 40 and ar >= en * 0.35:
        return "ar"
    if en >= 80 and ar <= max(5, int(en * 0.03)):
        return "en"
    return None


def set_html_attr(text: str, name: str, value: str) -> tuple[str, bool]:
    match = HTML_OPEN_RE.search(text)
    if not match:
        return text, False
    tag = match.group(0)
    attr_re = re.compile(ATTR_RE_TEMPLATE.format(name=re.escape(name)), re.I | re.S)
    if attr_re.search(tag):
        new_tag = attr_re.sub(f' {name}="{escape(value, quote=True)}"', tag, count=1)
    else:
        new_tag = tag[:-1] + f' {name}="{escape(value, quote=True)}">'
    return text[: match.start()] + new_tag + text[match.end() :], new_tag != tag


def canonical_for(route: str) -> str:
    route = (route or "").strip("/")
    return BASE_URL if not route else BASE_URL + route + "/"


def insert_before_head_close(text: str, fragment: str) -> tuple[str, bool]:
    match = HEAD_CLOSE_RE.search(text)
    if not match:
        return text, False
    prefix = "" if text[: match.start()].endswith("\n") else "\n"
    replacement = prefix + "  " + fragment + "\n"
    return text[: match.start()] + replacement + text[match.start() :], True


def ensure_title_from_h1(text: str) -> tuple[str, bool, str]:
    if TITLE_RE.search(text):
        return text, False, "title_already_present"
    h1s = [strip_tags(x) for x in H1_RE.findall(text)]
    h1s = [x for x in h1s if x]
    if len(h1s) != 1 or not (4 <= len(h1s[0]) <= 120):
        return text, False, "h1_not_uniquely_safe_for_title"
    title = f"<title>{escape(h1s[0])}</title>"
    new_text, changed = insert_before_head_close(text, title)
    return new_text, changed, "derived_exactly_from_existing_h1" if changed else "missing_head_close"


def normalize_canonical(text: str, route: str) -> tuple[str, bool, str]:
    target = canonical_for(route)
    matches = list(CANONICAL_RE.finditer(text))
    fragment = f'<link rel="canonical" href="{escape(target, quote=True)}">'
    if not matches:
        new_text, changed = insert_before_head_close(text, fragment)
        return new_text, changed, "inserted_self_canonical" if changed else "missing_head_close"
    start, end = matches[0].span()
    out = text[:start] + fragment + text[end:]
    for m in reversed(list(CANONICAL_RE.finditer(out))[1:]):
        out = out[: m.start()] + out[m.end() :]
    return out, out != text, "normalized_to_one_self_canonical"


def copy_description_from_og(text: str) -> tuple[str, bool, str]:
    if META_DESCRIPTION_RE.search(text):
        return text, False, "description_already_present"
    og = OG_DESCRIPTION_RE.search(text)
    if not og:
        return text, False, "no_existing_og_description"
    content = CONTENT_RE.search(og.group(0))
    if not content:
        return text, False, "og_description_has_no_content"
    value = re.sub(r"\s+", " ", content.group(2)).strip()
    if not (20 <= len(value) <= 320):
        return text, False, "og_description_length_not_safe"
    fragment = f'<meta name="description" content="{escape(value, quote=True)}">'
    new_text, changed = insert_before_head_close(text, fragment)
    return new_text, changed, "copied_exact_existing_og_description" if changed else "missing_head_close"


def stage_page(source: Path, target: Path, item: dict[str, Any]) -> dict[str, Any]:
    original = source.read_text(encoding="utf-8", errors="replace")
    text = original
    findings = set(item.get("findings") or [])
    actions = ((item.get("actions") or {}).get("safe_autofix") or [])
    safe_codes = {str(x.get("code")) for x in actions if isinstance(x, dict)}
    findings |= safe_codes
    changes: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    lang = infer_lang(text)
    if "missing_lang" in findings:
        if lang:
            text, changed = set_html_attr(text, "lang", lang)
            (changes if changed else skipped).append({"code": "missing_lang", "reason": f"inferred_{lang}" if changed else "html_tag_missing"})
        else:
            skipped.append({"code": "missing_lang", "reason": "language_not_deterministic"})

    if "missing_rtl" in findings:
        effective_lang = lang
        html_match = HTML_OPEN_RE.search(text)
        if html_match and re.search(r"\blang\s*=\s*([\"'])ar(?:-[^\"']*)?\1", html_match.group(0), re.I):
            effective_lang = "ar"
        if effective_lang == "ar":
            text, changed = set_html_attr(text, "dir", "rtl")
            (changes if changed else skipped).append({"code": "missing_rtl", "reason": "arabic_document" if changed else "html_tag_missing"})
        else:
            skipped.append({"code": "missing_rtl", "reason": "arabic_document_not_proven"})

    if "missing_title" in findings:
        text, changed, reason = ensure_title_from_h1(text)
        (changes if changed else skipped).append({"code": "missing_title", "reason": reason})

    if "canonical_count_not_one" in findings:
        text, changed, reason = normalize_canonical(text, str(item.get("route") or ""))
        (changes if changed else skipped).append({"code": "canonical_count_not_one", "reason": reason})

    if "missing_description" in findings:
        text, changed, reason = copy_description_from_og(text)
        (changes if changed else skipped).append({"code": "missing_description", "reason": reason})

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return {
        "path": source.name,
        "changed": text != original,
        "source_sha256": sha256_bytes(source.read_bytes()),
        "staged_sha256": sha256_bytes(target.read_bytes()),
        "changes": changes,
        "skipped": skipped,
    }


def build_staging(site: Path, plan: dict[str, Any], staging: Path) -> dict[str, Any]:
    before = tree_manifest(site)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    pages: list[dict[str, Any]] = []
    for item in plan.get("items") or []:
        rel = str(item.get("path") or "")
        if not rel or rel not in before:
            continue
        source = site / rel
        target = staging / rel
        if str(item.get("risk") or "standard") == "high" or str(item.get("gate") or "").startswith("blocked-"):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            pages.append({"path": rel, "changed": False, "source_sha256": before[rel], "staged_sha256": before[rel], "changes": [], "skipped": [{"code": "all", "reason": "high_risk_or_blocked_page"}]})
            continue
        result = stage_page(source, target, item)
        result["path"] = rel
        pages.append(result)

    after = tree_manifest(site)
    source_unchanged = before == after
    if not source_unchanged:
        raise RuntimeError("Source HTML tree changed while staging; refusing to continue")
    return {
        "version": VERSION,
        "status": "passed" if source_unchanged else "failed",
        "policy": "Staging only. No claim-level health content is generated or rewritten. High-risk/blocked pages are copied unchanged.",
        "source_unchanged": source_unchanged,
        "source_tree_sha256": sha256_bytes(json.dumps(before, sort_keys=True).encode()),
        "source_tree_sha256_after": sha256_bytes(json.dumps(after, sort_keys=True).encode()),
        "summary": {
            "eligible_pages": len(pages),
            "staged_changed": sum(bool(x["changed"]) for x in pages),
            "staged_unchanged": sum(not bool(x["changed"]) for x in pages),
            "changes": sum(len(x["changes"]) for x in pages),
            "skipped_actions": sum(len(x["skipped"]) for x in pages),
        },
        "pages": pages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--staging-dir", type=Path, default=Path("artifacts/site-quality-agent-v410/staging-v412"))
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/site-quality-agent-v410/staging-manifest-v412.json"))
    args = parser.parse_args()
    site = args.site.resolve()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    manifest = build_staging(site, plan, args.staging_dir.resolve())
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
