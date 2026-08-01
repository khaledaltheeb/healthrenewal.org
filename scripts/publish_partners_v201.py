#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

CORE = Path(__file__).with_name("publish_partners_v201_core.py")
spec = importlib.util.spec_from_file_location("publish_partners_v201_core", CORE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load partners v201 publisher core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

BASE = os.environ.get("SITE_BASE", "https://healthrenewal.org/").rstrip("/")
parsed = urlsplit(BASE)
if parsed.scheme not in {"http", "https"} or not parsed.netloc:
    raise SystemExit({"invalid_partners_base": BASE})
ROUTE = "/partners/"
URL = BASE + ROUTE

core.BASE = BASE
core.ROUTE = ROUTE
core.URL = URL

for name in dir(core):
    if name.startswith("__") or name in globals():
        continue
    globals()[name] = getattr(core, name)


def main() -> int:
    core.BASE = BASE
    core.ROUTE = ROUTE
    core.URL = URL
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    core.publish(site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
