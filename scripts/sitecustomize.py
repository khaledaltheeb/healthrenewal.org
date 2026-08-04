"""Fail-closed Rawafid audit hook for the final generated site."""
from __future__ import annotations

import atexit
import json
import os
import sys
import traceback
from pathlib import Path


def generated_site_target() -> Path | None:
    if Path(sys.argv[0]).name != "generate_sitemap_index_v304.py" or len(sys.argv) < 2:
        return None
    target = Path(sys.argv[1])
    return target.resolve() if target.name == "_site" else None


_TARGET = generated_site_target()


@atexit.register
def audit_generated_site() -> None:
    if _TARGET is None:
        return
    try:
        from rawafid_brand_consistency import normalize_root

        report = normalize_root(
            _TARGET,
            fix=True,
            production=True,
            report_path=_TARGET / "api/rawafid-brand-consistency-v3.json",
        )
        print(json.dumps({"rawafid_brand_consistency": report.status}, ensure_ascii=False))
        if report.status != "passed":
            os._exit(1)
    except BaseException:
        traceback.print_exc()
        os._exit(1)
