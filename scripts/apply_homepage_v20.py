from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import apply_homepage_v20_core_v221 as _core
from scripts.apply_homepage_v20_core_v221 import *  # noqa: F401,F403

_original_run_publisher = _core.run_publisher


def run_publisher(script: str) -> None:
    _original_run_publisher(script)
    if script == "publish_magazine_v201.py":
        _original_run_publisher("publish_articles_v221.py")


_core.run_publisher = run_publisher


if __name__ == "__main__":
    _core.main()
