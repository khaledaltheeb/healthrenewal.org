from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from urllib.parse import urlsplit

CORE = Path(__file__).with_name("publish_caregiver_wellbeing_v188_core.py")
spec = importlib.util.spec_from_file_location("publish_caregiver_wellbeing_v188_core", CORE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load caregiver wellbeing v188 publisher core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

BASE_URL = os.environ.get("SITE_BASE", "https://healthrenewal.org/").rstrip("/")
if not urlsplit(BASE_URL).netloc:
    raise SystemExit({"invalid_caregiver_base": BASE_URL})
core.BASE_URL = BASE_URL

for name in dir(core):
    if name.startswith("__") or name in globals():
        continue
    globals()[name] = getattr(core, name)


def main() -> None:
    core.BASE_URL = BASE_URL
    core.main()


if __name__ == "__main__":
    main()
