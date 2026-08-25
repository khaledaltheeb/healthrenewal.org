from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "scripts/publish_addiction_atlas_v2.py"

spec = importlib.util.spec_from_file_location("rawafid_addiction_atlas_v2", V2)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load addiction atlas v2 publisher")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

module.DATA_FILES = [
    ROOT / "data/addiction-atlas/substances-v1.json",
    ROOT / "data/addiction-atlas/substances-v2.json",
    ROOT / "data/addiction-atlas/substances-v3.json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish Rawafid Addiction Atlas v3 from three evidence data waves")
    parser.add_argument("site", nargs="?", default="_site")
    args = parser.parse_args()
    module.publish(Path(args.site))


if __name__ == "__main__":
    main()
