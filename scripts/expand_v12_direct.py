from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from site_base_path_v1 import normalize_site_base_path

LEGACY_PATH = Path(__file__).with_name("expand_v12_direct_legacy_v1.py")
SPEC = importlib.util.spec_from_file_location("expand_v12_direct_legacy_v1", LEGACY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load preserved v12 generator: {LEGACY_PATH}")
legacy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = legacy
SPEC.loader.exec_module(legacy)
legacy.BASE_PATH = normalize_site_base_path(legacy.BASE)


def main() -> None:
    legacy.BASE_PATH = normalize_site_base_path(legacy.BASE)
    legacy.main()


if __name__ == "__main__":
    main()
