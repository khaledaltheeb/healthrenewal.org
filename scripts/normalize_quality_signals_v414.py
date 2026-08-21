#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = 414
HTML_LANG_RE = re.compile(r"<html\b[^>]*\blang\s*=\s*([\"'])([^\"']+)\1", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style|svg|template|noscript)\b.*?</\1\s*>", re.I | re.S)
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
LATIN_RE = re.compile(r"[A-Za-z]")
OWNERSHIP_RE = re.compile(r"^(?:google[a-z0-9_-]+|bing(?:siteauth)?|yandex[_-]?[a-z0-9_-]+)\.html$", re.I)
CRITICAL_TERMS = (
    "انتحار", "إيذاء النفس", "ايذاء النفس", "جرعة زائدة", "جرعة دواء", "أدوية", "ادوية", "دواء",
    "سرطان", "كيماوي", "علاج كيميائي", "إشعاعي", "اشعاعي", "صرع", "نوبة صرع",
    "suicide", "self-harm", "self harm", "overdose", "medication", "chemotherapy", "radiotherapy", "cancer", "seizure",
)


def visible_text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def declared_lang(html: str) -> str:
    match = HTML_LANG_RE.search(html)
    return (match.group(2).strip().lower() if match else "")


def arabic_dominant(text: str) -> bool:
    ar = len(ARABIC_RE.findall(text))
    en = len(LATIN_RE.findall(text))
    return ar >= 40 and ar >= en * 0.35


def refined_high_risk(text: str, route: str) -> bool:
    folded = text.casefold()
    if any(term.casefold() in folded for term in CRITICAL_TERMS):
        return True
    route_folded = route.casefold()
    return any(x in route_folded for x in ("pediatric-oncology", "oncology", "self-harm", "suicide", "medication-safety"))


def recompute_priority(page: dict[str, Any]) -> int:
    return (
        100 - int(page.get("score") or 0)
        + (20 if page.get("risk") == "high" else 0)
        + (10 if int(page.get("authoritative_sources") or 0) == 0 else 0)
        + min(10, int(page.get("broken_internal_links") or 0) * 2)
    )


def normalize(site: Path, report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    original_pages = list(report.get("upgrade_queue") or [])
    before_high = sum(1 for p in original_pages if p.get("risk") == "high")
    corrected: list[dict[str, Any]] = []
    corrections: list[dict[str, Any]] = []
    excluded: list[str] = []

    for raw in original_pages:
        page = dict(raw)
        rel = str(page.get("path") or "")
        if OWNERSHIP_RE.fullmatch(Path(rel).name):
            excluded.append(rel)
            continue
        source = site / rel
        if not source.is_file():
            corrected.append(page)
            continue
        html = source.read_text(encoding="utf-8", errors="replace")
        text = visible_text(html)
        findings = set(page.get("findings") or [])
        score = int(page.get("score") or 0)
        page_changes: list[str] = []

        lang = declared_lang(html)
        if "missing_rtl" in findings and lang and not lang.startswith("ar"):
            findings.remove("missing_rtl")
            score = min(100, score + 3)
            page_changes.append(f"removed_missing_rtl_for_declared_{lang}")
        elif "missing_rtl" in findings and not arabic_dominant(text):
            findings.remove("missing_rtl")
            score = min(100, score + 3)
            page_changes.append("removed_missing_rtl_for_non_arabic_dominant_page")

        old_risk = str(page.get("risk") or "standard")
        new_risk = "high" if refined_high_risk(text, str(page.get("route") or "")) else "standard"
        page["risk"] = new_risk
        if old_risk == "high" and new_risk == "standard":
            if "high_risk_without_authoritative_source" in findings:
                findings.remove("high_risk_without_authoritative_source")
                if int(page.get("authoritative_sources") or 0) == 0:
                    findings.add("no_authoritative_source")
                score = min(100, score + 8)
            page_changes.append("downgraded_overbroad_high_risk_signal")

        page["score"] = score
        page["findings"] = sorted(findings)
        page["priority"] = recompute_priority(page)
        corrected.append(page)
        if page_changes:
            corrections.append({"path": rel, "changes": page_changes, "risk_before": old_risk, "risk_after": new_risk})

    corrected.sort(key=lambda p: (-int(p.get("priority") or 0), int(p.get("score") or 0), str(p.get("path") or "")))
    valid_paths = {str(p.get("path") or "") for p in corrected}
    dossiers = [d for d in (report.get("research_dossiers") or []) if str(d.get("path") or "") in valid_paths]
    visual = report.get("visual_audit") or {}
    summary = {
        "pages_scanned": len(corrected),
        "average_score": round(sum(int(p.get("score") or 0) for p in corrected) / len(corrected), 2) if corrected else 0,
        "pages_below_80": sum(int(p.get("score") or 0) < 80 for p in corrected),
        "high_risk_pages": sum(p.get("risk") == "high" for p in corrected),
        "broken_internal_links": sum(int(p.get("broken_internal_links") or 0) for p in corrected),
        "images_missing_alt": sum(int(p.get("missing_alt") or 0) for p in corrected),
        "css_files_scanned": int(visual.get("css_files_scanned") or 0),
        "low_contrast_css_pairs": int(visual.get("low_contrast_count") or 0),
        "research_dossiers": len(dossiers),
    }
    normalized = dict(report)
    normalized["version"] = VERSION
    normalized["source_version"] = report.get("version")
    normalized["summary"] = summary
    normalized["finding_counts"] = dict(Counter(code for p in corrected for code in (p.get("findings") or [])))
    normalized["upgrade_queue"] = corrected
    normalized["research_dossiers"] = dossiers
    normalized["signal_normalization"] = {
        "policy": "Generic words such as disorder/diagnosis/treatment do not by themselves trigger high-risk classification. Explicit page language overrides incidental bilingual fragments for RTL checks.",
        "high_risk_before": before_high,
        "high_risk_after": summary["high_risk_pages"],
        "corrected_pages": len(corrections),
        "excluded_non_content_files": excluded,
    }
    audit = {
        "version": VERSION,
        "status": "passed",
        "summary": normalized["signal_normalization"],
        "corrections": corrections,
    }
    return normalized, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--audit-output", type=Path, default=None)
    args = parser.parse_args()
    site = args.site.resolve()
    report_path = args.report.resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    raw_backup = report_path.with_name("report-v410-raw.json")
    if not raw_backup.exists():
        shutil.copy2(report_path, raw_backup)
    normalized, audit = normalize(site, report)
    report_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit_path = args.audit_output.resolve() if args.audit_output else report_path.with_name("signal-normalization-v414.json")
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
