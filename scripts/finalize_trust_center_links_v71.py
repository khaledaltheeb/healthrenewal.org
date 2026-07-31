from __future__ import annotations

import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
OPTIONAL_LINKS = (
    ("/pterminology-site/care-guides/", "care-guides/index.html"),
    ("/pterminology-site/daily-tools/", "daily-tools/index.html"),
)
EVIDENCE_HEADING = "المصادر والمراجعة والتصحيح"


def ensure_evidence_anchor(text: str) -> tuple[str, bool]:
    existing = re.findall(
        r"\bid\s*=\s*['\"]evidence['\"]",
        text,
        flags=re.I,
    )
    if len(existing) == 1:
        return text, False
    if len(existing) > 1:
        raise SystemExit("Trust center contains duplicate evidence anchors")

    pattern = re.compile(
        rf"<section(?P<attrs>[^>]*)>\s*(?=<h2>\s*{re.escape(EVIDENCE_HEADING)}\s*</h2>)",
        re.I | re.S,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise SystemExit("Trust evidence section is missing or ambiguous")

    attrs = matches[0].group("attrs")
    if re.search(r"\bid\s*=", attrs, flags=re.I):
        raise SystemExit("Trust evidence section already uses another identifier")

    updated, count = pattern.subn(
        lambda match: f'<section{match.group("attrs")} id="evidence">',
        text,
        count=1,
    )
    if count != 1 or len(re.findall(r"\bid\s*=\s*['\"]evidence['\"]", updated, re.I)) != 1:
        raise SystemExit("Trust evidence anchor could not be finalized uniquely")
    return updated, True


def finalize(site: Path = SITE) -> dict[str, object]:
    page = site / "trust" / "index.html"
    if not page.is_file():
        raise SystemExit("Missing generated trust center page")
    text = page.read_text(encoding="utf-8")
    removed: list[str] = []
    for href, target in OPTIONAL_LINKS:
        if (site / target).is_file():
            continue
        pattern = re.compile(rf'<a\s+href="{re.escape(href)}"[^>]*>.*?</a>', re.S)
        text, count = pattern.subn("", text, count=1)
        if count:
            removed.append(href)

    text, evidence_anchor_added = ensure_evidence_anchor(text)
    page.write_text(text, encoding="utf-8")
    return {
        "removed_optional_links": removed,
        "remaining_links": text.count("<a "),
        "evidence_anchor_added": evidence_anchor_added,
        "evidence_anchor_count": len(
            re.findall(r"\bid\s*=\s*['\"]evidence['\"]", text, re.I)
        ),
    }


if __name__ == "__main__":
    print(finalize())
