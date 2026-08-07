#!/usr/bin/env python3
"""Compatibility entrypoint for the current complete-site production finalizer.

The authoritative workflow historically invokes this v2 filename. Keep that
stable entrypoint while routing execution to v3, which adds the formal
special-needs v280/v281 publication repair and validation gates.
"""
from finalize_content_quality_v3 import main


if __name__ == '__main__':
    main()
