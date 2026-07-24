from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
ROOT = SITE / "cognitive-lab"

TYPO_FIXES = {
    "المتقدمةة": "المتقدمة",
    "الأساسيةة": "الأساسية",
}


def collapse_adjacent_phrases(value: str) -> str:
    text = " ".join(str(value or "").split())
    for old, new in TYPO_FIXES.items():
        text = text.replace(old, new)
    tokens = text.split(" ") if text else []
    changed = True
    while changed:
        changed = False
        max_size = min(4, len(tokens) // 2)
        for size in range(max_size, 0, -1):
            for index in range(0, len(tokens) - size * 2 + 1):
                if tokens[index:index + size] == tokens[index + size:index + size * 2]:
                    del tokens[index + size:index + size * 2]
                    changed = True
                    break
            if changed:
                break
    return " ".join(tokens)


def repeated_phrase(value: str) -> str:
    tokens = " ".join(str(value or "").split()).split(" ")
    for size in range(min(4, len(tokens) // 2), 0, -1):
        for index in range(0, len(tokens) - size * 2 + 1):
            if tokens[index:index + size] == tokens[index + size:index + size * 2]:
                return " ".join(tokens[index:index + size])
    return ""


def definition_from(text: str) -> tuple[re.Match[str], dict]:
    match = re.search(
        r'<script type="application/json" id="lab-definition">(.*?)</script>',
        text,
        re.S,
    )
    if not match:
        raise ValueError("missing lab-definition")
    return match, json.loads(match.group(1))


def main() -> None:
    pages = sorted(ROOT.glob("*/index.html"))
    if len(pages) != 53:
        raise SystemExit(f"Expected 53 cognitive pages before copy hardening, found {len(pages)}")

    fixes: list[dict[str, str]] = []
    title_replacements: dict[str, str] = {}
    for page in pages:
        text = page.read_text(encoding="utf-8")
        match, data = definition_from(text)
        old_title = str(data.get("title", "")).strip()
        new_title = collapse_adjacent_phrases(old_title)
        if not old_title or not new_title:
            raise SystemExit(f"Missing cognitive title: {page}")
        if old_title != new_title:
            title_replacements[old_title] = new_title
            text = text.replace(old_title, new_title)
            match, data = definition_from(text)
            data["title"] = new_title
            payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            text = text[:match.start(1)] + payload + text[match.end(1):]
            page.write_text(text, encoding="utf-8")
            fixes.append({"slug": page.parent.name, "before": old_title, "after": new_title})

    index_path = ROOT / "index.html"
    index_text = index_path.read_text(encoding="utf-8")
    for old_title, new_title in title_replacements.items():
        index_text = index_text.replace(old_title, new_title)
    index_path.write_text(index_text, encoding="utf-8")

    errors: list[str] = []
    titles: dict[str, str] = {}
    for page in pages:
        text = page.read_text(encoding="utf-8")
        _, data = definition_from(text)
        title = str(data.get("title", "")).strip()
        repeated = repeated_phrase(title)
        if repeated:
            errors.append(f"{page.parent.name}: repeated title phrase {repeated}")
        for typo in TYPO_FIXES:
            if typo in title:
                errors.append(f"{page.parent.name}: title typo {typo}")
        normalized = re.sub(r"\s+", " ", title).strip()
        if normalized in titles:
            errors.append(f"duplicate title after hardening: {title} / {titles[normalized]}")
        titles[normalized] = page.parent.name
        if title not in index_text:
            errors.append(f"{page.parent.name}: hardened title missing from cognitive index")

    report = {
        "version": 209,
        "status": "built-not-published",
        "cognitive_pages": len(pages),
        "changed_titles": len(fixes),
        "fixes": fixes,
        "adjacent_phrase_guard": True,
        "specific_typo_guard": sorted(TYPO_FIXES),
        "error_count": len(errors),
        "errors": errors,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "cognitive-copy-v209.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
