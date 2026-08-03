"""Production hook for the canonical Pages publisher.

When the final sitemap generator is executed against ``_site``, this module runs
the deterministic Rawafid brand normalizer after the generator exits. Python
loads ``sitecustomize`` automatically because the workflow executes scripts from
this directory.
"""
from __future__ import annotations

import atexit
import json
import os
import sys
import traceback
from pathlib import Path


def _target_root() -> Path | None:
    if Path(sys.argv[0]).name != "generate_sitemap_index_v304.py":
        return None
    if len(sys.argv) < 2:
        return None
    candidate = Path(sys.argv[1])
    return candidate if candidate.name == "_site" else None


_TARGET = _target_root()


@atexit.register
def _normalize_production_brand() -> None:
    if _TARGET is None:
        return
    try:
        from rawafid_brand_consistency import normalize_root

        report = normalize_root(
            _TARGET,
            fix=True,
            production=True,
            report_path=_TARGET / "api/rawafid-brand-consistency-v2.json",
        )
        print(json.dumps({"rawafid_brand_consistency": report.status}, ensure_ascii=False))
        if report.status != "passed":
            os._exit(1)
    except BaseException:
        traceback.print_exc()
        os._exit(1)
