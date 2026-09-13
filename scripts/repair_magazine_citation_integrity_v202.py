#!/usr/bin/env python3
"""Apply narrowly-scoped, evidence-verified citation repairs to a magazine tree.

This is not a generic search/replace pass. Every rule is tied to one known page
and exact old values. A rule refuses to modify a page when its expected old
value is missing, making accidental broad rewrites visible rather than silent.

The command is intended for build trees. Source HTML remains reviewable in git,
while production output receives the corrected citation chain. Once a source
page is regenerated from structured content the rule can be removed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str
    reason: str


REPAIRS: dict[str, tuple[Replacement, ...]] = {
    "pediatric-oncology/studies/family-resilience-childhood-cancer-qualitative-synthesis-2026/index.html": (
        Replacement(
            "10.3389/fpsyt.2026.1856540/full",
            "10.3389/fpsyt.2026.1856540",
            "Frontiers /full is an article route suffix, not part of the DOI.",
        ),
    ),
    "pediatric-oncology/theses/bridging-gap-hct-success-troullioud-lucas-2026/index.html": (
        Replacement(
            "10.1182/bloodadvances.2024013302",
            "10.1038/s41409-023-02121-1",
            "The linked title is Predictors of outcomes in HCT for Fanconi anemia; PubMed/Nature identify DOI 10.1038/s41409-023-02121-1.",
        ),
        Replacement(
            "10.1002/pbc.31048",
            "10.3389/fonc.2023.1221782",
            "The linked title concerns second HCT with cord blood after pediatric leukemia relapse; the matching Troullioud Lucas paper is Frontiers in Oncology 2023.",
        ),
        Replacement(
            "10.3389/fimmu.2023.1163408",
            "10.1016/j.jcyt.2023.05.012",
            "The linked title is Early immune reconstitution as predictor for outcomes after allogeneic HCT; PubMed identifies the Cytotherapy DOI.",
        ),
        Replacement(
            "دراسة Frontiers in Immunology لعام 2023 المرتبطة بالمؤلف",
            "دراسة Cytotherapy لعام 2023 المرتبطة بالمؤلف",
            "Correct journal for the early immune reconstitution study.",
        ),
        Replacement(
            "دراسة Pediatric Blood &amp; Cancer لعام 2024 المرتبطة بالأطروحة",
            "دراسة Frontiers in Oncology لعام 2023 المرتبطة بالأطروحة",
            "Correct journal and year for the second cord-blood HCT study.",
        ),
    ),
}


def apply_repairs(magazine_dir: Path, *, strict: bool = True) -> dict:
    results: list[dict] = []
    changed_pages = 0
    for rel_path, rules in REPAIRS.items():
        path = magazine_dir / rel_path
        if not path.is_file():
            if strict:
                raise SystemExit(f"Citation repair target is missing: {path}")
            results.append({"path": rel_path, "status": "missing", "changes": 0})
            continue

        original = path.read_text(encoding="utf-8", errors="strict")
        updated = original
        applied = 0
        for rule in rules:
            if rule.old not in updated:
                # Idempotence: a previously repaired page is valid when the new
                # value is already present and the old value is absent.
                if rule.new in updated:
                    continue
                if strict:
                    raise SystemExit(
                        f"Expected citation/text not found in {rel_path}: {rule.old}"
                    )
                continue
            updated = updated.replace(rule.old, rule.new)
            applied += 1

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_pages += 1
        results.append(
            {
                "path": rel_path,
                "status": "changed" if updated != original else "already_correct",
                "changes": applied,
            }
        )

    return {
        "schema_version": 1,
        "changed_pages": changed_pages,
        "rules": sum(len(rules) for rules in REPAIRS.values()),
        "results": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("magazine_dir", nargs="?", type=Path, default=ROOT / "magazine")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--non-strict", action="store_true")
    args = ap.parse_args()
    report = apply_repairs(args.magazine_dir.resolve(), strict=not args.non_strict)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
