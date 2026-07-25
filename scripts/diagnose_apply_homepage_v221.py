from __future__ import annotations

import json
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import apply_homepage_v20 as homepage

CONTRACT = 221
REPORT = homepage.SITE / "api" / "homepage-publisher-progress-v221.json"
ORIGINAL_RUN_PUBLISHER = homepage.run_publisher
LAST_COMPLETED: str | None = None


def stamp(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        **payload,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_target(script: str) -> None:
    if script == "publish_special_needs_guides_v217.py":
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "diagnose_special_needs_guides_v221.py"),
                str(homepage.SITE),
            ],
            check=True,
        )
        return
    ORIGINAL_RUN_PUBLISHER(script)


def traced_publisher(script: str) -> None:
    global LAST_COMPLETED
    stamp({"status": "running", "last_started": script, "last_completed": LAST_COMPLETED})
    try:
        run_target(script)
    except Exception as exc:
        stamp(
            {
                "status": "failed",
                "last_started": script,
                "last_completed": LAST_COMPLETED,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        raise
    LAST_COMPLETED = script
    stamp({"status": "running", "last_started": script, "last_completed": LAST_COMPLETED})


def main() -> None:
    homepage.run_publisher = traced_publisher
    stamp({"status": "starting", "last_started": None, "last_completed": None})
    try:
        homepage.main()
    except Exception as exc:
        current = {}
        if REPORT.is_file():
            try:
                current = json.loads(REPORT.read_text(encoding="utf-8"))
            except Exception:
                current = {}
        stamp(
            {
                "status": "failed",
                "last_started": current.get("last_started"),
                "last_completed": current.get("last_completed"),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        raise
    stamp({"status": "passed", "last_started": None, "last_completed": "all"})


if __name__ == "__main__":
    main()
