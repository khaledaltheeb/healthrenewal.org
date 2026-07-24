#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = Path(__file__).with_name("enhance_sitewide_seo_core_v216.py")
SECTION_PUBLISHER = Path(__file__).with_name("publish_section_directory_v217.py")
SECTION_API_NORMALIZER = Path(__file__).with_name("normalize_section_directory_api_v217.py")
CORE_TRAILER = '\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'

if not CORE.is_file():
    raise RuntimeError(f"Missing SEO core: {CORE}")

_core_source = CORE.read_text(encoding="utf-8")
if CORE_TRAILER not in _core_source:
    raise RuntimeError("SEO core entrypoint contract changed")
_core_source = _core_source.replace(CORE_TRAILER, "\n", 1)
exec(compile(_core_source, str(CORE), "exec"), globals())


def publish_section_directory() -> None:
    subprocess.run(
        [sys.executable, str(SECTION_PUBLISHER), str(SITE)],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(SECTION_API_NORMALIZER), str(SITE)],
        check=True,
    )


if __name__ == "__main__":
    publish_section_directory()
    raise SystemExit(main())
