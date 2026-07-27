#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOMEPAGE = ROOT / "scripts" / "apply_homepage_v20.py"
WRAPPER = ROOT / "scripts" / "publish_special_needs_guides_v217.py"
PIPELINE = ROOT / "scripts" / "publish_special_needs_guides_v217_pipeline_core.py"
CORE = ROOT / "scripts" / "publish_special_needs_guides_v217_core.py"
CLINICAL = ROOT / "scripts" / "publish_autism_clinical_pathways_v324.py"
CLINICAL_CORE = ROOT / "scripts" / "publish_autism_clinical_pathways_v324_core.py"
MANIFEST = ROOT / "content" / "v221" / "special-needs-guides-production-manifest-ar.json"
WORKFLOW = ROOT / ".github" / "workflows" / "integrate-special-needs-guides-v217.yml"


def require(text: str, marker: str, label: str, count: int = 1) -> None:
    actual = text.count(marker)
    if actual != count:
        raise SystemExit(f"{label}: expected {count}, found {actual}: {marker}")


def require_present(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise SystemExit(f"{label}: missing marker: {marker}")


def main() -> int:
    homepage = HOMEPAGE.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")
    core = CORE.read_text(encoding="utf-8")
    clinical = CLINICAL.read_text(encoding="utf-8")
    clinical_core = CLINICAL_CORE.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    require(homepage, 'run_publisher("publish_special_needs_guides_v217.py")', "production entrypoint")

    # Public wrapper: add v324 after the durable 25-guide pipeline.
    require(wrapper, "import publish_autism_clinical_pathways_v324 as clinical324", "v324 clinical import")
    require(wrapper, "import publish_special_needs_guides_v217_pipeline_core as pipeline", "25-guide pipeline import")
    require(wrapper, "reset_clinical_outputs(site)", "deterministic v324 reset")
    require(wrapper, "clinical_report = clinical324.publish(site)", "v324 publication call")

    # Pipeline core: preserve the fifth batch and all established condition layers.
    require(pipeline, "import publish_special_needs_guides_v214 as batch214", "fifth batch import")
    require(pipeline, "import publish_special_needs_guides_v217_core as core", "legacy core import")
    require(
        pipeline,
        'PRODUCTION_MANIFEST = ROOT / "content" / "v221" / "special-needs-guides-production-manifest-ar.json"',
        "production manifest reference",
    )
    require(core, "The four batches must produce twenty unique guide routes", "legacy 20-guide contract")

    # Clinical transport must remain digest-verified and review boundaries visible.
    require_present(clinical, "EXPECTED_B64_SHA256", "v324 Base64 digest contract")
    require_present(clinical, "EXPECTED_GZIP_SHA256", "v324 Gzip digest contract")
    require_present(clinical, "EXPECTED_JSON_SHA256", "v324 JSON digest contract")
    require_present(clinical_core, '"external_clinical_review_completed": False', "clinical review boundary")

    if manifest.get("version") != 221 or manifest.get("batches") != [209, 210, 211, 212, 214]:
        raise SystemExit("The v221 production manifest must declare the five ordered batches")
    if len(manifest.get("source_files", [])) != 25 or len(set(manifest["source_files"])) != 25:
        raise SystemExit("The v221 production manifest must declare 25 unique source files")
    missing = [path for path in manifest["source_files"] if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"The v221 production manifest references missing files: {missing}")

    forbidden = (
        "Commit production integration on main",
        "git push origin HEAD:main",
        "Enforce twenty special-needs guide production contract",
        "'special_needs_guides':'20/20'",
    )
    remaining = [marker for marker in forbidden if marker in workflow]
    if remaining:
        raise SystemExit(f"Legacy self-modifying workflow markers remain: {remaining}")

    print(
        {
            "legacy_core_guides": 20,
            "production_pipeline_guides": 25,
            "clinical_pathway_guides": 4,
            "batches": 5,
            "production_entrypoint": "single-layered-wrapper",
            "self_modifying_workflow": False,
            "status": "compatible",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
