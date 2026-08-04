"""Fail-closed Rawafid hooks for generated source and production outputs."""
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


def quick_info_source_target() -> Path | None:
    if Path(sys.argv[0]).name != "build_quick_info.py":
        return None
    return Path.cwd().resolve()


_GENERATED_TARGET = generated_site_target()
_QUICK_INFO_TARGET = quick_info_source_target()


def normalize_or_exit(root: Path, *, production: bool, report_path: Path) -> None:
    try:
        from rawafid_brand_consistency import normalize_root

        report = normalize_root(
            root,
            fix=True,
            production=production,
            report_path=report_path,
        )
        print(json.dumps({"rawafid_brand_consistency": report.status}, ensure_ascii=False))
        if report.status != "passed":
            os._exit(1)
    except BaseException:
        traceback.print_exc()
        os._exit(1)


@atexit.register
def normalize_quick_info_source() -> None:
    """Normalize newly rebuilt Quick Info pages before Git observes changes."""

    if _QUICK_INFO_TARGET is None:
        return
    normalize_or_exit(
        _QUICK_INFO_TARGET,
        production=False,
        report_path=_QUICK_INFO_TARGET / "reports/rawafid-brand-consistency-v3.json",
    )


@atexit.register
def audit_generated_site() -> None:
    """Normalize and fail closed on the final generated production artifact."""

    if _GENERATED_TARGET is None:
        return
    normalize_or_exit(
        _GENERATED_TARGET,
        production=True,
        report_path=_GENERATED_TARGET / "api/rawafid-brand-consistency-v3.json",
    )
