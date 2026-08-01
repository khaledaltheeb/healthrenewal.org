#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from urllib.parse import urlsplit

CORE = Path(__file__).with_name("publish_youth_sector_v353_base_core.py")
spec = importlib.util.spec_from_file_location("publish_youth_sector_v353_base_core", CORE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load youth sector v353 base core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

BASE = os.environ.get("SITE_BASE", "https://healthrenewal.org/").rstrip("/")
parsed = urlsplit(BASE)
base_path = parsed.path.strip("/")
BASE_PATH = f"/{base_path}/" if base_path else "/"
if not parsed.netloc or BASE_PATH.startswith("//"):
    raise SystemExit({"invalid_youth_base": BASE, "base_path": BASE_PATH})

core.BASE = BASE
core.BASE_PATH = BASE_PATH

for name in dir(core):
    if name.startswith("__") or name in globals():
        continue
    globals()[name] = getattr(core, name)
