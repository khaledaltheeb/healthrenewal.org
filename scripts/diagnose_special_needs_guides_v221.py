from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for candidate in (str(ROOT), str(SCRIPTS)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import publish_special_needs_guides_v217 as guides

CONTRACT = 221
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
REPORT = SITE / "api" / "special-needs-guides-progress-v221.json"
STATE: dict[str, Any] = {
    "status": "starting",
    "stage": "initialization",
    "last_batch_started": None,
    "last_batch_completed": None,
    "last_page_started": None,
    "last_page_completed": None,
}


def stamp(**updates: Any) -> None:
    STATE.update(updates)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        **STATE,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wrap_batch(version: int, publisher: Callable[[Path], dict[str, Any]]) -> Callable[[Path], dict[str, Any]]:
    def wrapped(site: Path) -> dict[str, Any]:
        stamp(status="running", stage="batch-publication", last_batch_started=version)
        try:
            result = publisher(site)
        except Exception as exc:
            stamp(
                status="failed",
                stage="batch-publication",
                last_batch_started=version,
                error_type=type(exc).__name__,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise
        stamp(status="running", stage="batch-publication", last_batch_completed=version)
        return result

    return wrapped


ORIGINAL_VALIDATE_PAGE = guides.validate_page
ORIGINAL_VALIDATE_DISCOVERY = guides.validate_discovery


def traced_validate_page(site: Path, slug: str, expected_title: str) -> dict[str, Any]:
    stamp(status="running", stage="page-validation", last_page_started=slug)
    try:
        result = ORIGINAL_VALIDATE_PAGE(site, slug, expected_title)
    except Exception as exc:
        stamp(
            status="failed",
            stage="page-validation",
            last_page_started=slug,
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise
    stamp(status="running", stage="page-validation", last_page_completed=slug)
    return result


def traced_validate_discovery(site: Path, slugs: list[str]) -> dict[str, Any]:
    stamp(status="running", stage="discovery-validation")
    try:
        result = ORIGINAL_VALIDATE_DISCOVERY(site, slugs)
    except Exception as exc:
        stamp(
            status="failed",
            stage="discovery-validation",
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise
    stamp(status="running", stage="discovery-validation-completed")
    return result


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing site directory: {SITE}")
    guides.BATCHES = tuple(
        (version, wrap_batch(version, publisher), manifest_path)
        for version, publisher, manifest_path in guides.BATCHES
    )
    guides.validate_page = traced_validate_page
    guides.validate_discovery = traced_validate_discovery
    stamp(status="running", stage="publisher-start")
    try:
        report = guides.publish(SITE)
    except BaseException as exc:
        if STATE.get("status") != "failed":
            stamp(
                status="failed",
                error_type=type(exc).__name__,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
        raise
    stamp(
        status="passed",
        stage="completed",
        guide_count=report.get("guide_count"),
        batch_count=report.get("batch_count"),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
