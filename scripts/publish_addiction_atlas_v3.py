from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "scripts/publish_addiction_atlas_v2.py"
MANIFEST = ROOT / "data/addiction-atlas/substance-waves.json"

spec = importlib.util.spec_from_file_location("rawafid_addiction_atlas_v2", V2)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load addiction atlas v2 publisher")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def registered_wave_paths() -> list[Path]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    routes = payload.get("waves") or []
    if not routes:
        raise RuntimeError("Addiction atlas wave manifest is empty")
    paths: list[Path] = []
    seen: set[str] = set()
    for route in routes:
        if not isinstance(route, str) or not route.startswith("/data/addiction-atlas/substances-v") or not route.endswith(".json"):
            raise RuntimeError(f"Invalid wave route: {route!r}")
        if route in seen:
            raise RuntimeError(f"Duplicate wave route: {route}")
        seen.add(route)
        path = ROOT / route.lstrip("/")
        if not path.is_file():
            raise RuntimeError(f"Missing registered wave: {route}")
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish Rawafid Addiction Atlas from the registered evidence-wave manifest")
    parser.add_argument("site", nargs="?", default="_site")
    args = parser.parse_args()
    module.DATA_FILES = registered_wave_paths()
    module.publish(Path(args.site))


if __name__ == "__main__":
    main()
