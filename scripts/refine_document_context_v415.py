#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = 415
SHELL_BLOCK_RE = re.compile(r"<(nav|header|footer|aside)\b[^>]*>.*?</\1\s*>", re.I | re.S)
SCRIPT_BLOCK_RE = re.compile(r"<(script|style|svg|template|noscript)\b[^>]*>.*?</\1\s*>", re.I | re.S)
MAIN_RE = re.compile(r"<(main|article)\b[^>]*>(.*?)</\1\s*>", re.I | re.S)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title\s*>", re.I | re.S)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1\s*>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
HTML_RE = re.compile(r"<html\b", re.I)
HEAD_RE = re.compile(r"<head\b", re.I)
BODY_RE = re.compile(r"<body\b", re.I)
CRITICAL_TERMS = (
    "انتحار", "إيذاء النفس", "ايذاء النفس", "جرعة زائدة", "جرعة دواء", "سلامة الدواء", "سلامة الأدوية",
    "سرطان", "كيماوي", "علاج كيميائي", "إشعاعي", "اشعاعي", "صرع", "نوبة صرع",
    "suicide", "self-harm", "self harm", "overdose", "medication safety", "chemotherapy", "radiotherapy", "cancer", "seizure",
)
PAGE_ONLY_FINDINGS = {
    "missing_lang", "missing_rtl", "missing_title", "canonical_count_not_one", "missing_description", "missing_h1", "missing_jsonld",
}
PAGE_ONLY_DEDUCTIONS = {
    "missing_lang": 3, "missing_rtl": 3, "missing_title": 8, "canonical_count_not_one": 6,
    "missing_description": 6, "missing_h1": 8, "missing_jsonld": 4,
}


def strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", value)).strip()


def classify_document(html: str) -> str:
    if HTML_RE.search(html) and HEAD_RE.search(html) and BODY_RE.search(html):
        return "document"
    return "editorial-fragment"


def main_html(html: str, kind: str) -> str:
    clean = SCRIPT_BLOCK_RE.sub(" ", html)
    if kind == "document":
        matches = MAIN_RE.findall(clean)
        if matches:
            return " ".join(body for _, body in matches)
        clean = SHELL_BLOCK_RE.sub(" ", clean)
    return clean


def context_text(html: str, route: str, kind: str) -> str:
    title = " ".join(strip_tags(x) for x in TITLE_RE.findall(html))
    h1 = " ".join(strip_tags(x) for x in H1_RE.findall(html))
    body = strip_tags(main_html(html, kind))
    return re.sub(r"\s+", " ", f"{route} {title} {h1} {body}").strip()


def is_high_risk(html: str, route: str, kind: str) -> bool:
    text = context_text(html, route, kind).casefold()
    return any(term.casefold() in text for term in CRITICAL_TERMS)


def recompute_priority(page: dict[str, Any]) -> int:
    return (
        100 - int(page.get("score") or 0)
        + (20 if page.get("risk") == "high" else 0)
        + (10 if int(page.get("authoritative_sources") or 0) == 0 else 0)
        + min(10, int(page.get("broken_internal_links") or 0) * 2)
    )


def refine(site: Path, report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    corrections: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    high_before = sum(1 for p in (report.get("upgrade_queue") or []) if p.get("risk") == "high")

    for raw in report.get("upgrade_queue") or []:
        page = dict(raw)
        rel = str(page.get("path") or "")
        source = site / rel
        if not source.is_file():
            pages.append(page)
            continue
        html = source.read_text(encoding="utf-8", errors="replace")
        kind = classify_document(html)
        counts[kind] += 1
        findings = set(page.get("findings") or [])
        score = int(page.get("score") or 0)
        changes: list[str] = []

        if kind == "editorial-fragment":
            removed = sorted(findings & PAGE_ONLY_FINDINGS)
            for code in removed:
                findings.remove(code)
                score = min(100, score + PAGE_ONLY_DEDUCTIONS[code])
            if removed:
                changes.append("removed_page_level_findings_from_fragment:" + ",".join(removed))

        old_risk = str(page.get("risk") or "standard")
        new_risk = "high" if is_high_risk(html, str(page.get("route") or ""), kind) else "standard"
        if old_risk != new_risk:
            changes.append(f"risk:{old_risk}->{new_risk}")
        if old_risk == "high" and new_risk == "standard" and "high_risk_without_authoritative_source" in findings:
            findings.remove("high_risk_without_authoritative_source")
            if int(page.get("authoritative_sources") or 0) == 0:
                findings.add("no_authoritative_source")
            score = min(100, score + 8)
        elif old_risk == "standard" and new_risk == "high" and int(page.get("authoritative_sources") or 0) == 0:
            if "no_authoritative_source" in findings:
                findings.remove("no_authoritative_source")
            findings.add("high_risk_without_authoritative_source")
            score = max(0, score - 8)

        page["artifact_type"] = kind
        page["risk"] = new_risk
        page["score"] = score
        page["findings"] = sorted(findings)
        page["priority"] = recompute_priority(page)
        pages.append(page)
        if changes:
            corrections.append({"path": rel, "artifact_type": kind, "changes": changes})

    pages.sort(key=lambda p: (-int(p.get("priority") or 0), int(p.get("score") or 0), str(p.get("path") or "")))
    visual = report.get("visual_audit") or {}
    valid_paths = {str(p.get("path") or "") for p in pages}
    dossiers = [d for d in (report.get("research_dossiers") or []) if str(d.get("path") or "") in valid_paths]
    summary = {
        "pages_scanned": len(pages),
        "documents": counts["document"],
        "editorial_fragments": counts["editorial-fragment"],
        "average_score": round(sum(int(p.get("score") or 0) for p in pages) / len(pages), 2) if pages else 0,
        "pages_below_80": sum(int(p.get("score") or 0) < 80 for p in pages),
        "high_risk_pages": sum(p.get("risk") == "high" for p in pages),
        "broken_internal_links": sum(int(p.get("broken_internal_links") or 0) for p in pages),
        "images_missing_alt": sum(int(p.get("missing_alt") or 0) for p in pages),
        "css_files_scanned": int(visual.get("css_files_scanned") or 0),
        "low_contrast_css_pairs": int(visual.get("low_contrast_count") or 0),
        "research_dossiers": len(dossiers),
    }
    out = dict(report)
    out["version"] = VERSION
    out["source_version"] = report.get("version")
    out["summary"] = summary
    out["finding_counts"] = dict(Counter(code for p in pages for code in (p.get("findings") or [])))
    out["upgrade_queue"] = pages
    out["research_dossiers"] = dossiers
    out["document_context_refinement"] = {
        "high_risk_before": high_before,
        "high_risk_after": summary["high_risk_pages"],
        "corrected_items": len(corrections),
        "documents": summary["documents"],
        "editorial_fragments": summary["editorial_fragments"],
        "policy": "Page-level SEO findings apply only to full HTML documents. Clinical risk is evaluated from main/article content with site chrome removed when possible.",
    }
    audit = {"version": VERSION, "status": "passed", "summary": out["document_context_refinement"], "corrections": corrections}
    return out, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--audit-output", type=Path, default=None)
    args = parser.parse_args()
    report_path = args.report.resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    backup = report_path.with_name("report-v414-pre-context.json")
    if not backup.exists():
        shutil.copy2(report_path, backup)
    refined, audit = refine(args.site.resolve(), report)
    report_path.write_text(json.dumps(refined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit_path = args.audit_output.resolve() if args.audit_output else report_path.with_name("document-context-v415.json")
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
