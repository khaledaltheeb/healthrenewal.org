#!/usr/bin/env python3
"""Compatibility entry point for the topic-specific undercovered-content engine.

The public contract remains v401 because central publishers and historical tests
consume that version. The maintained implementation is v403: specialized topic
contexts, anti-placeholder gates, language editing, and safety checkpoints.
"""

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from publish_undercovered_content_v403 import *  # noqa: E402,F401,F403
from publish_undercovered_content_v403 import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
