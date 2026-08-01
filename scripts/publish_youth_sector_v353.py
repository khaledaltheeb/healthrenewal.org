#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

CORE = Path(__file__).with_name("publish_youth_sector_v353_core.py")
spec = importlib.util.spec_from_file_location("publish_youth_sector_v353_core", CORE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load youth sector v353 publisher core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

BASE_PATH = core.BASE_PATH
TRUST_ROUTES = {
    "methodology": f"{BASE_PATH}trust/",
    "information_evaluation": f"{BASE_PATH}trust/",
}
_RETIRED_ROUTES = {
    f"{BASE_PATH}editorial-methodology/": TRUST_ROUTES["methodology"],
    f"{BASE_PATH}evaluate-mental-health-information/": TRUST_ROUTES["information_evaluation"],
}
core.TRUST_ROUTES = TRUST_ROUTES
core._RETIRED_ROUTES = _RETIRED_ROUTES

for name in dir(core):
    if name.startswith("__") or name in globals():
        continue
    globals()[name] = getattr(core, name)


def main() -> None:
    core.TRUST_ROUTES = TRUST_ROUTES
    core._RETIRED_ROUTES = _RETIRED_ROUTES
    core.main()


if __name__ == "__main__":
    main()
