#!/usr/bin/env python3
"""Build a non-destructive inventory of every HTML page across all Git refs.

The audit never edits, deletes, redirects, truncates, or regenerates a page. It identifies
all historical variants for each path, scores the richest candidate, flags likely
placeholder/baseline regressions, and emits machine-readable and human-readable plans.
Any actual merge remains a separate reviewed change.
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

TAG_RE = re.compile(r"<[^>]+>", re.S)
SCRIPT_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.U)
HEADING_RE = re.compile(r"<h([1-3])\b[^>]*>(.*?)</h\1>", re.I | re.S)
SECTION_RE = re.compile(r"<(section|article)\b", re.I)
SCHEMA_RE = re.compile(r"application/ld\+json", re.I)
PLACEHOLDER_PATTERNS = (
    r"قريب[ًاا]", r"coming\s+soon", r"under\s+construction", r"page\s+template",
    r"placeholder", r"lorem\s+ipsum", r"baseline", r"سيتم\s+إضافة", r"المحتوى\s+قيد",
)
PLACEHOLDER_RE = re.compile("|".join(PLACEHOLDER_PATTERNS), re.I)
RESERVED_PATHS = {
    "magazine/feed.xml",
    "magazine/index.html",
    "scripts/expand_v12_direct.py",
    "scripts/complete_core_sections_v15.py",
    "scripts/expand_v12_direct_legacy_v1.py",
    "scripts/complete_core_sections_v15_legacy_v1.py",
    "scripts/site_base_path_v1.py",
}


def git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], text=True, capture_output=True)
    if check and proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def clean_text(source: str) -> str:
    source = COMMENT_RE.sub(" ", source)
    source = SCRIPT_RE.sub(" ", source)
    source = TAG_RE.sub(" ", source)
    return html_lib.unescape(re.sub(r"\s+", " ", source)).strip()


def title_of(source: str) -> str:
    match = re.search(r"<title\b[^>]*>(.*?)</title>", source, re.I | re.S)
    return clean_text(match.group(1)) if match else ""


def h1_of(source: str) -> str:
    match = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)
    return clean_text(match.group(1)) if match else ""


@dataclass(frozen=True)
class Metrics:
    bytes: int
    words: int
    headings: int
    sections: int
    links: int
    references: int
    schema_blocks: int
    has_rtl: bool
    has_print_css: bool
    placeholder_hits: int
    title: str
    h1: str
    digest: str
    score: float


def metrics(source: str) -> Metrics:
    text = clean_text(source)
    words = len(WORD_RE.findall(text))
    headings = len(HEADING_RE.findall(source))
    sections = len(SECTION_RE.findall(source))
    links = len(re.findall(r"<a\b[^>]+href=", source, re.I))
    references = len(re.findall(r"(?:doi\.org|pubmed|who\.int|nice\.org\.uk|cochrane|references|المراجع|المصادر)", source, re.I))
    schema_blocks = len(SCHEMA_RE.findall(source))
    placeholder_hits = len(PLACEHOLDER_RE.findall(text))
    title = title_of(source)
    h1 = h1_of(source)
    has_rtl = bool(re.search(r"(?:dir=[\"']rtl|lang=[\"']ar)", source, re.I))
    has_print_css = bool(re.search(r"@media\s+print", source, re.I))
    score = (
        words
        + headings * 24
        + sections * 18
        + links * 3
        + references * 30
        + schema_blocks * 18
        + (35 if has_rtl else 0)
        + (20 if has_print_css else 0)
        + (15 if title else 0)
        + (20 if h1 else 0)
        - placeholder_hits * 220
    )
    return Metrics(
        bytes=len(source.encode("utf-8", errors="replace")), words=words,
        headings=headings, sections=sections, links=links, references=references,
        schema_blocks=schema_blocks, has_rtl=has_rtl, has_print_css=has_print_css,
        placeholder_hits=placeholder_hits, title=title, h1=h1,
        digest=hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest(),
        score=round(score, 2),
    )


def refs() -> list[str]:
    raw = git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes", "refs/tags")
    values = []
    for ref in raw.splitlines():
        if ref.endswith("/HEAD") or ref.startswith("refs/pull/"):
            continue
        values.append(ref)
    head = git("rev-parse", "HEAD").strip()
    values.append(head)
    return sorted(set(values))


def html_paths(ref: str) -> list[str]:
    output = git("ls-tree", "-r", "--name-only", ref, check=False)
    return [p for p in output.splitlines() if p.endswith((".html", ".htm"))]


def show(ref: str, path: str) -> str | None:
    proc = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True)
    if proc.returncode:
        return None
    return proc.stdout.decode("utf-8", errors="replace")


def commit_time(ref: str) -> str:
    return git("show", "-s", "--format=%cI", ref, check=False).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/full-content-recovery-v1")
    parser.add_argument("--max-variants", type=int, default=60)
    args = parser.parse_args()

    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    all_refs = refs()
    variants: dict[str, dict[str, dict]] = defaultdict(dict)

    for ref in all_refs:
        ref_time = commit_time(ref)
        for path in html_paths(ref):
            source = show(ref, path)
            if source is None:
                continue
            item = metrics(source)
            # Deduplicate identical blobs while preserving every ref that contains the version.
            entry = variants[path].setdefault(item.digest, {
                "metrics": asdict(item), "refs": [], "latestCommitTime": ref_time,
            })
            entry["refs"].append(ref)
            if ref_time > entry.get("latestCommitTime", ""):
                entry["latestCommitTime"] = ref_time

    head_ref = git("rev-parse", "HEAD").strip()
    pages = []
    regressions = []
    reserved_hits = []
    for path, digest_map in sorted(variants.items()):
        ordered = sorted(
            digest_map.values(),
            key=lambda x: (
                x["metrics"]["score"], x["metrics"]["words"],
                x["metrics"]["references"], x["metrics"]["bytes"],
            ),
            reverse=True,
        )[: args.max_variants]
        current_source = show(head_ref, path)
        current = metrics(current_source) if current_source is not None else None
        best = ordered[0] if ordered else None
        reason = []
        status = "current-is-richest"
        if current is None:
            status = "missing-from-current"
            reason.append("المسار موجود في تاريخ Git أو فرع آخر لكنه غير موجود في HEAD الحالي.")
        elif best and best["metrics"]["digest"] != current.digest:
            bm = best["metrics"]
            if current.placeholder_hits and not bm["placeholder_hits"]:
                status = "probable-placeholder-regression"
                reason.append("النسخة الحالية تحمل مؤشرات قالب/صفحة خط أساس بينما النسخة التاريخية لا تحملها.")
            elif bm["words"] >= current.words + 120 or bm["score"] >= current.score * 1.12:
                status = "richer-historical-candidate"
                reason.append("توجد نسخة تاريخية أغنى بوضوح في الكلمات أو البنية أو المراجع.")
            else:
                status = "historical-variant-review"
                reason.append("توجد نسخة مختلفة تستحق مقارنة تحريرية قبل الدمج.")
        if current and current.words < 120 and best and best["metrics"]["words"] >= 450:
            status = "probable-truncation-regression"
            reason.append("النسخة الحالية قصيرة جدًا مقارنة بنسخة تاريخية كاملة.")
        if path in RESERVED_PATHS:
            reserved_hits.append(path)
        page = {
            "path": path,
            "status": status,
            "reserved": path in RESERVED_PATHS,
            "current": asdict(current) if current else None,
            "recommendedBase": best,
            "reason": reason,
            "variants": ordered,
            "mergeRule": "اعتماد النسخة الأغنى كأساس ثم دمج المعلومات الفريدة فقط بعد مراجعة بشرية؛ يمنع الحذف والاختصار والتحويل إلى redirect.",
        }
        pages.append(page)
        if status != "current-is-richest":
            regressions.append(page)

    report = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "head": head_ref,
        "refsScanned": len(all_refs),
        "pagesDiscovered": len(pages),
        "pagesNeedingReview": len(regressions),
        "reservedPathsSkipped": sorted(reserved_hits),
        "policy": {
            "nonDestructive": True,
            "noDelete": True,
            "noTruncate": True,
            "noRedirectAsRecovery": True,
            "separateReviewedMergeRequired": True,
        },
        "pages": pages,
    }
    (root / "inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# تقرير استعادة النسخ الكاملة v1", "",
        f"- HEAD: `{head_ref}`",
        f"- المراجع المفحوصة: **{len(all_refs)}**",
        f"- مسارات HTML المكتشفة: **{len(pages)}**",
        f"- المسارات التي تحتاج مراجعة: **{len(regressions)}**", "",
        "## قواعد التنفيذ", "",
        "- لا حذف، لا اختصار، لا استبدال بصفحة تحويل.",
        "- تُعتمد النسخة الأغنى كأساس ثم تُدمج المعلومات الفريدة من بقية النسخ دون تكرار أو تناقض.",
        "- الملفات المحجوزة تُسجّل فقط ولا تُعدّل.", "",
        "## أعلى المرشحين للاستعادة", "",
        "| المسار | الحالة | كلمات الحالية | كلمات المرشح | السبب |",
        "|---|---:|---:|---:|---|",
    ]
    ranked = sorted(regressions, key=lambda p: ((p["recommendedBase"] or {"metrics": {"words": 0}})["metrics"]["words"] - ((p["current"] or {}).get("words", 0))), reverse=True)
    for page in ranked[:500]:
        current_words = (page["current"] or {}).get("words", 0)
        best_words = (page["recommendedBase"] or {"metrics": {"words": 0}})["metrics"]["words"]
        reason = " ".join(page["reason"]).replace("|", "\\|")
        lines.append(f"| `{page['path']}` | {page['status']} | {current_words} | {best_words} | {reason} |")
    (root / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # The audit itself fails only when it cannot inspect meaningful history.
    if len(all_refs) < 2 or len(pages) < 50:
        raise SystemExit("recovery audit coverage is unexpectedly small")
    print(json.dumps({k: report[k] for k in ("head", "refsScanned", "pagesDiscovered", "pagesNeedingReview")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
