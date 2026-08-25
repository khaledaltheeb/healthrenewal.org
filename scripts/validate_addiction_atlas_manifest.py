from __future__ import annotations

import json
from pathlib import Path

import validate_addiction_atlas_v2 as validator

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/addiction-atlas/substance-waves.json"


def main():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    waves = payload.get("waves") or []
    if not waves:
        raise AssertionError("substance wave manifest is empty")
    paths = []
    seen = set()
    for route in waves:
        if not isinstance(route, str) or not route.startswith("/data/addiction-atlas/substances-v") or not route.endswith(".json"):
            raise AssertionError(f"invalid substance wave route: {route!r}")
        if route in seen:
            raise AssertionError(f"duplicate substance wave route: {route}")
        seen.add(route)
        path = ROOT / route.lstrip("/")
        if not path.is_file():
            raise AssertionError(f"manifest points to missing substance wave: {route}")
        paths.append(path)
    validator.DATA_FILES = paths
    validator.main()


if __name__ == "__main__":
    main()
