#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CORE = Path(__file__).with_name("enhance_sitewide_seo_core_v216.py")
SECTION_PUBLISHER = Path(__file__).with_name("publish_section_directory_v217.py")
SECTION_API_NORMALIZER = Path(__file__).with_name("normalize_section_directory_api_v217.py")
HIDDEN_COLLECTIONS_ENHANCER = Path(__file__).with_name("enhance_hidden_collections_seo_v217.py")
HIDDEN_COLLECTIONS_VERIFIER = Path(__file__).with_name("verify_hidden_collections_seo_v217.py")
CORE_TRAILER = '\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'

for required in (
    CORE,
    SECTION_PUBLISHER,
    SECTION_API_NORMALIZER,
    HIDDEN_COLLECTIONS_ENHANCER,
    HIDDEN_COLLECTIONS_VERIFIER,
):
    if not required.is_file():
        raise RuntimeError(f"Missing SEO production component: {required}")

_core_source = CORE.read_text(encoding="utf-8")
if CORE_TRAILER not in _core_source:
    raise RuntimeError("SEO core entrypoint contract changed")
_core_source = _core_source.replace(CORE_TRAILER, "\n", 1)
exec(compile(_core_source, str(CORE), "exec"), globals())


def run_component(path: Path) -> None:
    subprocess.run(
        [sys.executable, str(path), str(SITE)],
        check=True,
    )


def publish_section_directory() -> None:
    run_component(SECTION_PUBLISHER)
    run_component(SECTION_API_NORMALIZER)


def enhance_hidden_collections() -> None:
    run_component(HIDDEN_COLLECTIONS_ENHANCER)
    run_component(HIDDEN_COLLECTIONS_VERIFIER)


if __name__ == "__main__":
    publish_section_directory()
    status = main()
    if status not in (None, 0):
        raise SystemExit(status)
    enhance_hidden_collections()
    raise SystemExit(0)
