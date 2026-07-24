from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
VERSION = "213"
RUNTIME_SUFFIX = "assets/js/lab-v12.js"
SCRIPT_RE = re.compile(
    r'(<script\b[^>]*\bsrc=["\'])([^"\']*assets/js/lab-v12\.js)(?:\?[^"\']*)?(["\'][^>]*>\s*</script>)',
    re.IGNORECASE,
)


def lab_pages() -> list[Path]:
    pages: list[Path] = []
    for root_name in ("assessment-lab", "cognitive-lab"):
        root = SITE / root_name
        if not root.is_dir():
            raise SystemExit(f"Missing generated lab root: {root}")
        pages.extend(sorted(root.rglob("*.html")))
    return sorted(set(pages))


def version_page(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    matches = list(SCRIPT_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one lab runtime in {path}, found {len(matches)}")

    def replace(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}?v={VERSION}{match.group(3)}"

    updated = SCRIPT_RE.sub(replace, text, count=1)
    if updated.count(f"{RUNTIME_SUFFIX}?v={VERSION}") != 1:
        raise SystemExit(f"Versioned runtime marker missing or duplicated in {path}")
    if re.search(r'assets/js/lab-v12\.js(?:["\'])', updated):
        raise SystemExit(f"Unversioned lab runtime remains in {path}")
    changed = updated != text
    if changed:
        path.write_text(updated, encoding="utf-8")
    return changed, updated


def main() -> None:
    pages = lab_pages()
    if len(pages) != 95:
        raise SystemExit(f"Expected 95 lab HTML pages (40 assessments + 53 cognitive + 2 indexes), found {len(pages)}")

    changed = 0
    cognitive = 0
    assessments = 0
    for page in pages:
        was_changed, _ = version_page(page)
        changed += int(was_changed)
        relative = page.relative_to(SITE).as_posix()
        cognitive += int(relative.startswith("cognitive-lab/"))
        assessments += int(relative.startswith("assessment-lab/"))

    runtime = SITE / RUNTIME_SUFFIX
    if not runtime.is_file():
        raise SystemExit(f"Missing generated runtime: {runtime}")
    runtime_text = runtime.read_text(encoding="utf-8")
    required_stroop_markers = [
        "mode==='stroop_basic'||mode==='stroop_advanced'",
        "stimulusInk",
        "stimulusWord",
        "#b42318",
        "#175cd3",
        "#067647",
        "#b54708",
        "#6941c6",
        "#087e8b",
    ]
    missing = [marker for marker in required_stroop_markers if marker not in runtime_text]
    if missing:
        raise SystemExit(f"Generated Stroop runtime is incomplete: {missing}")

    report = {
        "version": 213,
        "status": "built-not-published",
        "pages_scanned": len(pages),
        "assessment_pages": assessments,
        "cognitive_pages": cognitive,
        "pages_changed": changed,
        "versioned_runtime_url": f"/{RUNTIME_SUFFIX}?v={VERSION}",
        "unversioned_runtime_pages": 0,
        "duplicate_runtime_pages": 0,
        "stroop_palette_colors": 6,
        "stroop_inline_ink": True,
        "cache_busting_required": True,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-asset-cache-v213.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
