#!/usr/bin/env python3
from __future__ import annotations

try:
    from .apply_homepage_v20_core import *  # type: ignore[F403]  # noqa: F401,F403
    from . import apply_homepage_v20_core as _core
except ImportError:
    from apply_homepage_v20_core import *  # type: ignore[F403]  # noqa: F401,F403
    import apply_homepage_v20_core as _core


_original_run_publisher = _core.run_publisher


def _run_publisher_with_lab_guidance(script: str) -> None:
    if script == "enhance_sitewide_seo_v216.py":
        _original_run_publisher("expand_lab_guidance_v217.py")
    _original_run_publisher(script)


def main() -> None:
    _core.run_publisher = _run_publisher_with_lab_guidance
    _core.main()


if __name__ == "__main__":
    main()
