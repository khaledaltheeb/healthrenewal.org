#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

CORE = Path(__file__).with_name("publish_homepage_i18n_v72_core.py")
spec = importlib.util.spec_from_file_location("publish_homepage_i18n_v72_core", CORE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load multilingual homepage v72 publisher core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = os.environ.get("SITE_BASE", "https://healthrenewal.org/").rstrip("/")
parsed = urlsplit(BASE)
base_path = parsed.path.strip("/")
BASE_PATH = f"/{base_path}/" if base_path else "/"
if not parsed.netloc or BASE_PATH.startswith("//"):
    raise SystemExit({"invalid_i18n_base": BASE, "base_path": BASE_PATH})

core.SITE = SITE
core.BASE = BASE
core.BASE_PATH = BASE_PATH

for name in dir(core):
    if name.startswith("__") or name in globals():
        continue
    globals()[name] = getattr(core, name)


def main() -> None:
    core.SITE = SITE
    core.BASE = BASE
    core.BASE_PATH = BASE_PATH
    core.main()


if __name__ == "__main__":
    main()
