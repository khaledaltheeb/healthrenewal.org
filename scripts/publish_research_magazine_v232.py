#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from research_magazine_v232_core import CONTENT, load_data
from research_magazine_v232_publish import publish

__all__ = ["CONTENT", "load_data", "publish"]

if __name__ == "__main__":
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    publish(output)
