#!/usr/bin/env python3
"""Compatibility entry point for the topic-specific undercovered-content engine.

The public contract remains v401 because central publishers and historical tests
consume that version. The implementation is maintained in v402, which adds
specialized contexts, risks, measures, examples, and anti-boilerplate gates.
"""

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from publish_undercovered_content_v402 import *  # noqa: E402,F401,F403
from publish_undercovered_content_v402 import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
