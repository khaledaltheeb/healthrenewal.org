#!/usr/bin/env python3
"""Compatibility entry point for the topic-specific undercovered-content engine.

The public contract remains v401 because central publishers and historical tests
consume that version. The implementation is maintained in v402, which adds
specialized contexts, risks, measures, examples, and anti-boilerplate gates.
"""

from publish_undercovered_content_v402 import *  # noqa: F401,F403
from publish_undercovered_content_v402 import main


if __name__ == "__main__":
    raise SystemExit(main())
