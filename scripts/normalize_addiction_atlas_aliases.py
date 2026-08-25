from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/addiction-atlas/substance-waves.json"
ALIAS_KEYS = (
    "english_name_ar_transliteration",
    "search_aliases_ar",
    "search_aliases_en",
    "common_misspellings_ar",
    "common_misspellings_en",
    "spacing_variants",
    "hyphenation_variants",
    "legacy_spellings",
)


def dedupe(values):
    if not isinstance(values, list):
        return values, False
    output = []
    seen = set()
    changed = False
    for value in values:
        if not isinstance(value, str):
            output.append(value)
            continue
        cleaned = value.strip()
        if not cleaned:
            changed = True
            continue
        key = cleaned.casefold()
        if key in seen:
            changed = True
            continue
        seen.add(key)
        output.append(cleaned)
        if cleaned != value:
            changed = True
    return output, changed


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    routes = manifest.get("waves") or []
    if not routes:
        raise SystemExit("empty substance wave manifest")

    files_changed = 0
    values_removed = 0
    for route in routes:
        path = ROOT / route.lstrip("/")
        if not path.is_file():
            raise SystemExit(f"missing registered wave: {route}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for item in payload.get("substances", []):
            for key in ALIAS_KEYS:
                if key not in item:
                    continue
                before = item[key]
                after, key_changed = dedupe(before)
                if key_changed:
                    values_removed += max(0, len(before) - len(after)) if isinstance(before, list) and isinstance(after, list) else 0
                    item[key] = after
                    changed = True
        if changed:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            files_changed += 1

    print(json.dumps({"filesChanged": files_changed, "duplicateOrBlankAliasesRemoved": values_removed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
