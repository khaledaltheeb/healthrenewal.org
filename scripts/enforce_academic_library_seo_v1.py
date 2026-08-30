from __future__ import annotations

"""Scoped adapter for Rawafid academic-library technical SEO.

Reuses the repository's proven head-only SEO engine while narrowing ownership to
/library/branches, /library/therapies and /library/research. The adapter also
removes obsolete meta-keywords, gives this scope its own schema/marker profile,
and redirects the durable report away from other agents' report namespaces.
"""

import hashlib
import json
import re
from pathlib import Path

import enforce_tools_assessment_seo_v1 as core

PROFILE = "academic-library-seo-v1"
SCOPE_ROOTS = ("library/branches", "library/therapies", "library/research")
SECTION_NAMES = {
    "library/branches": "فروع علم النفس",
    "library/therapies": "العلاجات والتدخلات النفسية",
    "library/research": "مناهج البحث والقياس",
}

core.PROFILE = PROFILE
core.SCOPE_ROOTS = SCOPE_ROOTS
core.SECTION_NAMES = SECTION_NAMES
core.OWN_SCHEMA_RE = re.compile(
    r"(?is)\s*<script\b[^>]*data-rawafid-seo\s*=\s*([\"'])academic-library-seo-v1\1[^>]*>.*?</script\s*>\s*"
)
core.MARKER_RE = re.compile(
    r"(?is)\s*<!--\s*rawafid-academic-library-seo:v1\s+fingerprint=[0-9a-f]{24}\s*-->\s*"
)


def root_and_section(path: Path, site: Path) -> tuple[str, str]:
    parts = path.relative_to(site).parts
    if len(parts) < 2 or parts[0] != "library" or parts[1] not in {"branches", "therapies", "research"}:
        raise ValueError(f"outside owned academic-library scope: {path.relative_to(site)}")
    root = f"library/{parts[1]}"
    return root, SECTION_NAMES[root]


core.root_and_section = root_and_section


def clean_unverified_hreflang(head: str, site: Path) -> tuple[str, int]:
    """Academic library currently has no verified translation registry: emit none."""
    removed = 0
    out: list[str] = []
    cursor = 0
    for match in core.LINK_TAG_RE.finditer(head):
        out.append(head[cursor:match.start()])
        tag = match.group(0)
        if core.attrs(tag).get("hreflang"):
            removed += 1
        else:
            out.append(tag)
        cursor = match.end()
    out.append(head[cursor:])
    return "".join(out), removed


core.clean_broken_hreflang = clean_unverified_hreflang

_orig_build_plan = core.build_plan


def _remove_meta_keywords(head: str) -> tuple[str, int]:
    removed = 0
    out: list[str] = []
    cursor = 0
    for match in core.META_TAG_RE.finditer(head):
        out.append(head[cursor:match.start()])
        data = core.attrs(match.group(0))
        if data.get("name", "").lower() == "keywords":
            removed += 1
        else:
            out.append(match.group(0))
        cursor = match.end()
    out.append(head[cursor:])
    return "".join(out), removed


def build_plan(path, site, title_counts, desc_counts, intent_counts):
    plan = _orig_build_plan(path, site, title_counts, desc_counts, intent_counts)
    if plan is None:
        return None

    updated = plan.updated.replace(
        "rawafid-tools-assessment-seo:v1",
        "rawafid-academic-library-seo:v1",
    )
    hm = core.HEAD_RE.search(updated)
    if not hm:
        raise ValueError("missing head after scoped adaptation")
    head, removed = _remove_meta_keywords(hm.group(2))
    changes = list(plan.changes)
    if removed:
        changes.append(f"remove-meta-keywords:{removed}")
    updated = updated[: hm.start(2)] + head + updated[hm.end(2) :]

    fingerprint_source = json.dumps(
        {
            "profile": PROFILE,
            "path": plan.rel,
            "body": plan.body_hash,
            "title": plan.title,
            "description": plan.description,
            "canonical": plan.url,
            "primaryIntent": plan.primary_intent,
            "changes": changes,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:24]
    updated = re.sub(
        r"(?is)<!--\s*rawafid-academic-library-seo:v1\s+fingerprint=[0-9a-f]{24}\s*-->",
        f"<!-- rawafid-academic-library-seo:v1 fingerprint={fingerprint} -->",
        updated,
        count=1,
    )
    if changes and "rawafid-academic-library-seo:v1" not in updated:
        hm2 = core.HEAD_RE.search(updated)
        if not hm2:
            raise ValueError("head missing while restoring scoped fingerprint")
        marked = hm2.group(2).rstrip() + f"\n<!-- rawafid-academic-library-seo:v1 fingerprint={fingerprint} -->\n"
        updated = updated[: hm2.start(2)] + marked + updated[hm2.end(2) :]

    if core.raw_body_hash(updated) != plan.body_hash:
        raise ValueError("visible/raw body changed in academic-library adapter")
    return core.PagePlan(
        plan.path,
        plan.rel,
        plan.url,
        plan.root,
        plan.section,
        plan.topic,
        plan.title,
        plan.description,
        plan.primary_intent,
        plan.body_hash,
        plan.original,
        updated,
        sorted(set(changes)),
        fingerprint,
    )


core.build_plan = build_plan

_orig_verify_page = core.verify_page


def verify_page(plan, site, sitemap):
    _orig_verify_page(plan, site, sitemap)
    source = plan.path.read_text(encoding="utf-8")
    hm = core.HEAD_RE.search(source)
    if not hm:
        raise ValueError("head missing after scoped verification")
    head = hm.group(2)
    if core.get_meta(head, "name", "keywords"):
        raise ValueError("meta-keywords remain")
    if any(core.attrs(tag).get("hreflang") for tag in core.LINK_TAG_RE.findall(head)):
        raise ValueError("unverified hreflang remains")


core.verify_page = verify_page

_orig_write_json = core.write_json


def write_json(path: Path, value):
    if path.name == "tools-assessment-seo-v1.json":
        path = path.with_name("academic-library-seo-v1.json")
    _orig_write_json(path, value)


core.write_json = write_json


def main(argv=None) -> int:
    return core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
