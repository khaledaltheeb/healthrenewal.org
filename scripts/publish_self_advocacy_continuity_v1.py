#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import publish_self_advocacy_base_v170 as base

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "learning-paths" / "self-advocacy" / "service-transition-and-continuity-plan.json"
TARGET_RELATIVE = base.TARGET_RELATIVE
CANONICAL_ROUTE = base.CANONICAL_ROUTE
CANONICAL_URL = base.CANONICAL_URL
START = "<!-- self-advocacy-continuity-v1:start -->"
END = "<!-- self-advocacy-continuity-v1:end -->"
VERSION = 1


def strip_existing(source: str) -> str:
    return re.sub(re.escape(START) + r".*?" + re.escape(END), "", source, flags=re.S)


def validate(data: dict[str, Any]) -> None:
    base.validate_package(SOURCE, data)
    if data.get("id") != "self-advocacy-service-transition-continuity-v1":
        raise SystemExit("Unexpected service-continuity package ID")
    workflow = data.get("workflow") or []
    if len(workflow) != 7 or [item.get("step") for item in workflow] != list(range(1, 8)):
        raise SystemExit("Service-continuity workflow must contain seven ordered stages")
    if sum(len(item.get("questions", [])) for item in workflow) < 28:
        raise SystemExit("Service-continuity workflow is missing practical questions")
    if len(data.get("red_flags", [])) < 10 or len(data.get("quick_checklist", [])) < 9:
        raise SystemExit("Service-continuity safeguards are incomplete")
    internal_links = data.get("internal_links") or []
    if not internal_links or any(not link.startswith("/") or not link.endswith("/") for link in internal_links):
        raise SystemExit("Service-continuity internal links are invalid")
    serialized = json.dumps(data, ensure_ascii=False)
    for marker in (
        "ما يجب ألا ينقطع",
        "أقل قدر لازم",
        "تأكيد الاستلام",
        "الخطة المؤقتة",
        "فترة التداخل أو الفراغ",
        "30 و90 يومًا",
        "لا توجد شراكة",
    ):
        if marker not in serialized:
            raise SystemExit(f"Service-continuity marker missing: {marker}")


def route_exists(site: Path, route: str) -> bool:
    relative = route.strip("/")
    candidates = [site / relative, site / relative / "index.html", site / f"{relative}.html"]
    return any(path.is_file() for path in candidates)


def publish(site: Path) -> dict[str, Any]:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing service-continuity source: {SOURCE}")
    data = base.load_json(SOURCE)
    validate(data)

    target = site / TARGET_RELATIVE
    if not target.is_file():
        raise SystemExit(f"Missing existing self-advocacy page: {target}")
    source = target.read_text(encoding="utf-8", errors="replace")
    if source.count(f'<link rel="canonical" href="{CANONICAL_URL}">') != 1:
        raise SystemExit("Self-advocacy page does not have the expected single canonical")
    if base.START not in source or base.END not in source:
        raise SystemExit("Core self-advocacy packages must be published before continuity plan")

    clean = strip_existing(source)
    rendered = base.render_package(
        SOURCE.name,
        "خطة انتقال الخدمة واستمراريتها في المناصرة الذاتية",
        data,
    )
    block = START + "\n" + rendered + "\n" + END
    updated = clean.replace(base.END, block + "\n" + base.END, 1)
    if updated.count(START) != 1 or updated.count(END) != 1:
        raise SystemExit("Service-continuity insertion is not idempotent")
    if updated.count(f'<link rel="canonical" href="{CANONICAL_URL}">') != 1:
        raise SystemExit("Canonical changed during service-continuity publication")
    if updated.count(f'data-source-package="{SOURCE.name}"') != 1:
        raise SystemExit("Service-continuity source was not rendered exactly once")
    target.write_text(updated, encoding="utf-8")

    missing_links = [link for link in data["internal_links"] if not route_exists(site, link)]
    report = {
        "version": VERSION,
        "status": "passed" if not missing_links else "passed_with_integrity_followup",
        "canonicalRoute": CANONICAL_ROUTE,
        "canonicalUrl": CANONICAL_URL,
        "generatedPage": TARGET_RELATIVE.as_posix(),
        "sourcePackage": SOURCE.relative_to(ROOT).as_posix(),
        "standalonePagesCreated": 0,
        "mergedIntoExistingPage": True,
        "workflowStages": len(data["workflow"]),
        "practicalQuestions": sum(len(item.get("questions", [])) for item in data["workflow"]),
        "redFlags": len(data["red_flags"]),
        "internalLinks": len(data["internal_links"]),
        "missingInternalLinksBeforeFinalIntegrity": missing_links,
        "externalReviewCompleted": False,
        "outputBytes": len(updated.encode("utf-8")),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "self-advocacy-continuity-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
