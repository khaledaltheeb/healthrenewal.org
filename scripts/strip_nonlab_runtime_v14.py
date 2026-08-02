from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
PATTERN = re.compile(
    r"<script\b[^>]*\bsrc\s*=\s*([\"'])(?:https?://(?:khaledaltheeb\.github\.io|healthrenewal\.org))?/assets/js/lab-v12\.js(?:\?[^\"']*)?\1[^>]*>\s*</script>",
    re.IGNORECASE,
)
LAB_ROOTS = ("assessment-lab/", "cognitive-lab/", "assessments/", "cognitive-tests/")
VERIFY = "google644f1f7a8b7aaa2b.html"


def main() -> None:
    if not SITE.exists():
        raise SystemExit(f"Site root not found: {SITE}")
    removed = 0
    kept = 0
    residual: list[str] = []
    for page in SITE.rglob("*.html"):
        rel = page.relative_to(SITE).as_posix()
        if rel == VERIFY:
            continue
        text = page.read_text(encoding="utf-8")
        matches = len(PATTERN.findall(text))
        if any(rel.startswith(root) for root in LAB_ROOTS):
            kept += matches
            continue
        new, count = PATTERN.subn("", text)
        removed += count
        if count:
            page.write_text(new, encoding="utf-8")
        if PATTERN.search(new):
            residual.append(rel)
    if residual:
        raise SystemExit(f"Residual lab runtime on non-lab pages: {residual[:20]}")
    report_path = SITE / "api" / "performance-v14.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["regex_removed_lab_script_tags"] = removed
    report["total_removed_lab_script_tags"] = int(report.get("removed_lab_script_tags", 0)) + removed
    report["kept_lab_script_tags_after_regex"] = kept
    report["residual_lab_script_tags_non_lab"] = 0
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
