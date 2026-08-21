#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

VERSION = 411

SAFE_AUTOFIX = {
    "missing_lang": "Set the document language from visible Arabic/English content.",
    "missing_rtl": "Set dir=rtl for Arabic pages.",
    "missing_title": "Derive a page title from the existing H1 without inventing new claims.",
    "canonical_count_not_one": "Normalize to one self-referencing canonical URL.",
}
TECHNICAL_REVIEW = {
    "broken_internal_links": "Repair or remove broken internal destinations after route resolution.",
    "images_missing_alt": "Add context-specific alternative text after inspecting the image purpose.",
    "hero_inline_background_without_explicit_text_color": "Set explicit foreground colors and verify runtime contrast.",
    "missing_jsonld": "Add schema appropriate to the page type and validate it.",
    "missing_description": "Write a unique factual meta description grounded only in existing page content.",
}
EDITORIAL_RESEARCH = {
    "very_thin_content": "Rebuild the page around the user intent, evidence, examples, limitations and practical guidance.",
    "thin_content": "Expand only where the page has genuine unanswered user questions; avoid filler.",
    "no_authoritative_source": "Add direct authoritative sources supporting the page's material claims.",
}
SPECIALIST_REVIEW = {
    "high_risk_without_authoritative_source": "Do not publish new health claims until authoritative evidence is verified claim-by-claim.",
    "overcertain_health_claim": "Remove or qualify absolute health claims after specialist/editorial review.",
}


def classify(findings: list[str]) -> dict[str, list[dict[str, str]]]:
    buckets = {"safe_autofix": [], "technical_review": [], "editorial_research": [], "specialist_review": []}
    for code in sorted(set(findings)):
        if code in SAFE_AUTOFIX:
            buckets["safe_autofix"].append({"code": code, "action": SAFE_AUTOFIX[code]})
        elif code in TECHNICAL_REVIEW:
            buckets["technical_review"].append({"code": code, "action": TECHNICAL_REVIEW[code]})
        elif code in EDITORIAL_RESEARCH:
            buckets["editorial_research"].append({"code": code, "action": EDITORIAL_RESEARCH[code]})
        elif code in SPECIALIST_REVIEW:
            buckets["specialist_review"].append({"code": code, "action": SPECIALIST_REVIEW[code]})
        else:
            buckets["technical_review"].append({"code": code, "action": "Review this finding before changing the page."})
    return buckets


def evidence_index(dossiers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("path", "")): item for item in dossiers if item.get("path")}


def wave_for(page: dict[str, Any], actions: dict[str, list[dict[str, str]]]) -> str:
    if actions["specialist_review"]:
        return "wave-0-clinical-safety"
    if int(page.get("score", 100)) < 60 or str(page.get("risk")) == "high":
        return "wave-1-critical-quality"
    if int(page.get("score", 100)) < 80 or actions["editorial_research"]:
        return "wave-2-editorial-upgrade"
    if actions["technical_review"] or actions["safe_autofix"]:
        return "wave-3-technical-polish"
    return "wave-4-maintenance"


def build(report: dict[str, Any]) -> dict[str, Any]:
    pages = list(report.get("upgrade_queue") or [])
    dossiers = list(report.get("research_dossiers") or [])
    evidence = evidence_index(dossiers)
    items: list[dict[str, Any]] = []
    wave_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()

    for page in pages:
        actions = classify(list(page.get("findings") or []))
        wave = wave_for(page, actions)
        wave_counts[wave] += 1
        for bucket, entries in actions.items():
            action_counts[bucket] += len(entries)
        dossier = evidence.get(str(page.get("path", "")))
        provider_hits = 0
        if dossier:
            provider_hits = sum(len(v) for v in (dossier.get("providers") or {}).values() if isinstance(v, list))
        gate = "ready-for-safe-autofix"
        if actions["specialist_review"]:
            gate = "blocked-specialist-review"
        elif actions["editorial_research"] and not dossier:
            gate = "needs-evidence-research"
        elif actions["editorial_research"] and provider_hits == 0:
            gate = "needs-better-evidence"
        elif actions["editorial_research"]:
            gate = "evidence-candidates-ready-for-verification"
        elif actions["technical_review"]:
            gate = "needs-technical-review"
        items.append({
            "path": page.get("path"),
            "route": page.get("route"),
            "title": page.get("title") or page.get("h1"),
            "score": page.get("score"),
            "priority": page.get("priority"),
            "risk": page.get("risk"),
            "wave": wave,
            "gate": gate,
            "actions": actions,
            "research": {
                "available": dossier is not None,
                "query": dossier.get("query") if dossier else None,
                "candidate_count": provider_hits,
                "official_targets": dossier.get("official_targets", []) if dossier else [],
            },
            "acceptance": [
                "Re-run site_quality_agent_v410.py and do not regress the page score.",
                "No broken internal links introduced.",
                "No new absolute medical or psychological claim without claim-level evidence.",
                "Verify title/H1/meta description remain aligned with the actual page intent.",
                "For visual changes, verify foreground/background contrast and mobile rendering.",
            ],
        })

    wave_order = {
        "wave-0-clinical-safety": 0,
        "wave-1-critical-quality": 1,
        "wave-2-editorial-upgrade": 2,
        "wave-3-technical-polish": 3,
        "wave-4-maintenance": 4,
    }
    items.sort(key=lambda x: (wave_order[str(x["wave"])], -int(x.get("priority") or 0), str(x.get("path") or "")))
    return {
        "version": VERSION,
        "status": "passed",
        "source_version": report.get("version"),
        "policy": {
            "safe_autofix": "Only structural metadata may be changed automatically; no medical/psychological claim text is generated or rewritten.",
            "evidence": "Search results are candidate evidence, not proof. Verify relevance, population, design, recency and limitations before editing claim-level content.",
            "publication": "Clinical-safety items are blocked until specialist/editorial review is recorded.",
        },
        "summary": {
            "pages": len(items),
            "waves": dict(wave_counts),
            "action_counts": dict(action_counts),
            "blocked_specialist_review": sum(1 for x in items if x["gate"] == "blocked-specialist-review"),
            "needs_evidence_research": sum(1 for x in items if x["gate"] in {"needs-evidence-research", "needs-better-evidence"}),
            "ready_for_safe_autofix": sum(1 for x in items if x["gate"] == "ready-for-safe-autofix"),
        },
        "items": items,
    }


def markdown(plan: dict[str, Any]) -> str:
    s = plan["summary"]
    lines = [
        "# Site Upgrade Plan v411",
        "",
        f"- Pages in plan: {s['pages']}",
        f"- Blocked for specialist review: {s['blocked_specialist_review']}",
        f"- Need evidence research: {s['needs_evidence_research']}",
        f"- Ready for structural safe-autofix: {s['ready_for_safe_autofix']}",
        "",
        "## Priority queue",
        "",
    ]
    for item in plan["items"][:300]:
        lines.append(f"### {item['path']}")
        lines.append(f"- Wave: `{item['wave']}`")
        lines.append(f"- Gate: `{item['gate']}`")
        lines.append(f"- Score/Priority: `{item['score']}` / `{item['priority']}`")
        for bucket, entries in item["actions"].items():
            if entries:
                lines.append(f"- {bucket}: " + ", ".join(e["code"] for e in entries))
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/site-quality-agent-v410"))
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    plan = build(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "upgrade-plan-v411.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "upgrade-plan-v411.md").write_text(markdown(plan), encoding="utf-8")
    print(json.dumps(plan["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
