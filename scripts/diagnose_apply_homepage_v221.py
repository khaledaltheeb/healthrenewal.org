from __future__ import annotations

import json
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import apply_homepage_v20 as homepage

CONTRACT = 323
REPORT = homepage.SITE / "api" / "homepage-publisher-progress-v221.json"
LAST_COMPLETED: str | None = None
OUTPUT_LIMIT = 16_000
PROMOTED_HEADINGS = 0


class PublisherExecutionError(RuntimeError):
    def __init__(self, script: str, returncode: int, stdout: str, stderr: str) -> None:
        self.script = script
        self.returncode = returncode
        self.stdout = stdout[-OUTPUT_LIMIT:]
        self.stderr = stderr[-OUTPUT_LIMIT:]
        super().__init__(
            f"{script} exited with {returncode}; "
            f"stdout={self.stdout!r}; stderr={self.stderr!r}"
        )


def stamp(payload: dict) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract": CONTRACT,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        **payload,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_semantic_homepage_source() -> int:
    source = homepage.SOURCE
    if not source.is_file():
        raise RuntimeError(f"Homepage source is missing: {source}")

    text = source.read_text(encoding="utf-8")
    pattern = re.compile(r'<p class="item-title">([^<]+)</p>')
    transformed, promoted = pattern.subn(r'<h3 class="item-title">\1</h3>', text)
    total_h3 = len(re.findall(r'<h3\b', transformed))

    if promoted < 11:
        raise RuntimeError(
            f"Expected at least 11 homepage card titles to promote, found {promoted}"
        )
    if total_h3 < 16:
        raise RuntimeError(
            f"Semantic homepage source still has fewer than 16 H3 headings: {total_h3}"
        )

    generated_source = homepage.SITE.parent / ".homepage-semantic-v323.html"
    generated_source.write_text(transformed, encoding="utf-8")
    homepage.SOURCE = generated_source
    return promoted


def execute(script: str, command: list[str]) -> None:
    result = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise PublisherExecutionError(script, result.returncode, result.stdout, result.stderr)


def run_target(script: str) -> None:
    if script == "publish_special_needs_guides_v217.py":
        command = [
            sys.executable,
            str(ROOT / "scripts" / "diagnose_special_needs_guides_v221.py"),
            str(homepage.SITE),
        ]
    else:
        command = [
            sys.executable,
            str(ROOT / "scripts" / script),
            str(homepage.SITE),
        ]
    execute(script, command)


def traced_publisher(script: str) -> None:
    global LAST_COMPLETED
    stamp({"status": "running", "last_started": script, "last_completed": LAST_COMPLETED})
    try:
        run_target(script)
    except Exception as exc:
        payload = {
            "status": "failed",
            "last_started": script,
            "last_completed": LAST_COMPLETED,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        if isinstance(exc, PublisherExecutionError):
            payload.update(
                {
                    "returncode": exc.returncode,
                    "publisher_stdout": exc.stdout,
                    "publisher_stderr": exc.stderr,
                }
            )
        stamp(payload)
        raise
    LAST_COMPLETED = script
    stamp({"status": "running", "last_started": script, "last_completed": LAST_COMPLETED})


def verify_linked_sections() -> list[str]:
    expected = (
        "daily-tools/index.html",
        "learning-paths/index.html",
        "sitemap-tools-paths.xml",
        "api/daily-tools-v24.json",
    )
    missing = [relative for relative in expected if not (homepage.SITE / relative).is_file()]
    if missing:
        raise RuntimeError(f"Homepage-linked production sections are missing: {missing}")
    return list(expected)


def main() -> None:
    global PROMOTED_HEADINGS
    homepage.run_publisher = traced_publisher
    stamp({"status": "starting", "last_started": None, "last_completed": None})
    try:
        PROMOTED_HEADINGS = prepare_semantic_homepage_source()
        homepage.main()
        verified_sections = verify_linked_sections()
    except Exception as exc:
        current = {}
        if REPORT.is_file():
            try:
                current = json.loads(REPORT.read_text(encoding="utf-8"))
            except Exception:
                current = {}
        payload = {
            "status": "failed",
            "last_started": current.get("last_started"),
            "last_completed": current.get("last_completed"),
            "promoted_homepage_card_headings": PROMOTED_HEADINGS,
            "error_type": current.get("error_type", type(exc).__name__),
            "error": current.get("error", str(exc)),
            "traceback": current.get("traceback", traceback.format_exc()),
        }
        for key in ("returncode", "publisher_stdout", "publisher_stderr"):
            if key in current:
                payload[key] = current[key]
        stamp(payload)
        raise
    stamp(
        {
            "status": "passed",
            "last_started": None,
            "last_completed": "all",
            "promoted_homepage_card_headings": PROMOTED_HEADINGS,
            "verified_linked_sections": verified_sections,
        }
    )


if __name__ == "__main__":
    main()
