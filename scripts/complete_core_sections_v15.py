from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from publish_evidence_literacy_library_v322 import publish as publish_evidence_literacy
from site_base_path_v1 import normalize_site_base_path

LEGACY_PATH = Path(__file__).with_name("complete_core_sections_v15_legacy_v1.py")
SPEC = importlib.util.spec_from_file_location("complete_core_sections_v15_legacy_v1", LEGACY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load preserved v15 generator: {LEGACY_PATH}")
legacy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = legacy
SPEC.loader.exec_module(legacy)
legacy.BASE_PATH = normalize_site_base_path(legacy.BASE)

# Preserve the historical import surface for tests and other publishers that
# import helpers from complete_core_sections_v15 instead of executing it.
for _name in dir(legacy):
    if not _name.startswith("_"):
        globals().setdefault(_name, getattr(legacy, _name))

SITE = legacy.SITE
BASE = legacy.BASE
BASE_PATH = legacy.BASE_PATH


def evidence_contract_snapshot() -> dict[str, Any]:
    """Expose the existing v322 publication contract without duplicating main().

    The preserved generator invokes and enforces this contract during its normal
    run. This callable keeps the established static/import API visible to CI and
    to downstream tooling while the legacy implementation remains byte intact.
    """
    evidence = publish_evidence_literacy(SITE)
    if evidence.get("version") != 322 or evidence.get("status") != "passed":
        raise SystemExit({"invalid_evidence_literacy_v322": evidence})
    if evidence.get("guide_count") != 4 or int(evidence.get("minimum_guide_words", 0)) < 900:
        raise SystemExit({"insufficient_evidence_literacy_v322": evidence})
    return {
        "evidence_literacy_guides": evidence["guide_count"],
        "evidence_literacy_sources": evidence["source_count"],
        "evidence_literacy_minimum_words": evidence["minimum_guide_words"],
    }


def main() -> None:
    legacy.BASE_PATH = normalize_site_base_path(legacy.BASE)
    globals()["BASE_PATH"] = legacy.BASE_PATH
    legacy.main()


if __name__ == "__main__":
    main()
