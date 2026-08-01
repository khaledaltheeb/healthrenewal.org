#!/usr/bin/env python3
"""Compatibility entry point for the 100-page undercovered-content contract.

The public contract remains v401. The maintained chain is:
v402 topic-specific composition -> v403 language/safety editing -> v404 stable reporting.
The generated HTML identifies itself as engine v403 because v404 changes only
report determinism, not page content.
"""

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from publish_undercovered_content_v404 import *  # noqa: E402,F401,F403
from publish_undercovered_content_v404 import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
