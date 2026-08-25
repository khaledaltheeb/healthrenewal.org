from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data/addiction-atlas"
OUTPUT = DATA_DIR / "substances-all.json"
WAVE_RE = re.compile(r"^substances-v(\d+)\.json$")


def wave_files() -> list[Path]:
    found: list[tuple[int, Path]] = []
    for path in DATA_DIR.glob("substances-v*.json"):
        match = WAVE_RE.match(path.name)
        if match:
            found.append((int(match.group(1)), path))
    return [path for _, path in sorted(found)]


def main() -> None:
    waves = wave_files()
    if not waves:
        raise SystemExit("No addiction atlas substance waves found")

    merged: dict[str, dict] = {}
    source_versions: list[dict] = []
    for path in waves:
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_versions.append({
            "file": path.name,
            "schema_version": payload.get("schema_version"),
            "version": payload.get("version"),
            "updated_on": payload.get("updated_on"),
            "records": len(payload.get("substances", [])),
        })
        for item in payload.get("substances", []):
            slug = item.get("slug")
            if not slug:
                raise SystemExit(f"Missing slug in {path.name}")
            if slug in merged:
                raise SystemExit(f"Duplicate substance slug across waves: {slug}")
            merged[slug] = item

    substances = sorted(
        merged.values(),
        key=lambda item: (str(item.get("display_name_ar", "")), str(item.get("display_name_en", ""))),
    )
    result = {
        "schema_version": "rawafid-addiction-atlas-merged-v1",
        "version": "1.0.0",
        "updated_on": max((entry.get("updated_on") or "") for entry in source_versions),
        "generated_from": source_versions,
        "substance_count": len(substances),
        "notes_ar": "ملف مولد آلياً من جميع موجات substances-v*.json. لا تعدله يدوياً؛ عدل ملف الموجة المصدر ثم أعد البناء.",
        "substances": substances,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "passed",
        "waves": [p.name for p in waves],
        "substances": len(substances),
        "output": str(OUTPUT.relative_to(ROOT)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
