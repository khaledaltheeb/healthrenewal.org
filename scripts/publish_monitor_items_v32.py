from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERSION = 32
EXPECTED_SHARDS = 6
EXPECTED_PROFILES = 36
EXPECTED_ITEMS_PER_PROFILE = 12
EXPECTED_TOTAL_ITEMS = EXPECTED_PROFILES * EXPECTED_ITEMS_PER_PROFILE
ALLOWED_POLICIES = {"burden_tracking", "readiness_gaps", "safety_flags"}
GENERIC_SUFFIXES = (
    "كان هذا الجانب صعبًا أو أثر في يومي",
    "احتجت إلى دعم إضافي في هذا الجانب",
    "أريد متابعة تغير هذا الجانب",
)
DEFINITION_RE = re.compile(
    r'(<script type="application/json" id="lab-definition">)(.*?)(</script>)',
    re.S,
)


def load_definition(source: str) -> dict:
    match = DEFINITION_RE.search(source)
    if not match:
        raise ValueError("missing lab-definition")
    return json.loads(match.group(2).replace("<\\/", "</"))


def write_definition(source: str, definition: dict) -> str:
    payload = json.dumps(
        definition,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    updated, count = DEFINITION_RE.subn(
        lambda match: match.group(1) + payload + match.group(3),
        source,
        count=1,
    )
    if count != 1:
        raise ValueError("lab-definition replacement failed")
    return updated


def load_profiles(root: Path) -> tuple[dict[str, dict], list[str]]:
    shard_dir = root / "content" / "v32" / "monitor-items"
    shards = sorted(shard_dir.glob("part*.json"))
    if len(shards) != EXPECTED_SHARDS:
        raise SystemExit(
            f"Expected {EXPECTED_SHARDS} monitor item shards, found {len(shards)}"
        )
    profiles: dict[str, dict] = {}
    shard_names: list[str] = []
    for shard in shards:
        data = json.loads(shard.read_text(encoding="utf-8"))
        if data.get("version") != VERSION:
            raise SystemExit(f"Invalid shard version: {shard}")
        rows = data.get("profiles")
        if not isinstance(rows, dict) or not rows:
            raise SystemExit(f"Missing profiles in {shard}")
        overlap = sorted(set(profiles) & set(rows))
        if overlap:
            raise SystemExit(f"Duplicate profile slugs across shards: {overlap}")
        profiles.update(rows)
        shard_names.append(shard.relative_to(root).as_posix())
    if len(profiles) != EXPECTED_PROFILES:
        raise SystemExit(
            f"Expected {EXPECTED_PROFILES} monitor profiles, found {len(profiles)}"
        )
    return profiles, shard_names


def validate_profile(slug: str, profile: dict) -> list[str]:
    errors: list[str] = []
    title = profile.get("title")
    period = profile.get("period")
    options = profile.get("options")
    items = profile.get("items")
    policy = profile.get("monitor_policy")
    direction = profile.get("monitor_direction")
    critical = profile.get("critical_item_indices")
    summary = profile.get("summary")

    if not isinstance(title, str) or len(title.strip()) < 4:
        errors.append("invalid title")
    if not isinstance(period, str) or not period.strip():
        errors.append("invalid period")
    if not isinstance(summary, str) or len(summary.strip()) < 35:
        errors.append("summary too short")
    if policy not in ALLOWED_POLICIES:
        errors.append(f"invalid monitor_policy={policy!r}")
    if not isinstance(direction, str) or "لا تعني تشخيصًا" not in direction:
        errors.append("monitor direction must reject diagnosis")
    if not isinstance(options, list) or len(options) != 5:
        errors.append("expected exactly five options")
    elif len(set(map(str, options))) != 5:
        errors.append("duplicate options")
    if not isinstance(items, list) or len(items) != EXPECTED_ITEMS_PER_PROFILE:
        errors.append(f"expected {EXPECTED_ITEMS_PER_PROFILE} items")
    else:
        for index, item in enumerate(items):
            if not isinstance(item, str):
                errors.append(f"item {index} is not text")
                continue
            normalized = " ".join(item.split())
            if len(normalized) < 35:
                errors.append(f"item {index} too short")
            if ":" not in normalized and "：" not in normalized:
                errors.append(f"item {index} lacks domain anchor")
            if any(suffix in normalized for suffix in GENERIC_SUFFIXES):
                errors.append(f"item {index} contains generic template")
        if len(set(items)) != len(items):
            errors.append("duplicate items inside profile")
    if not isinstance(critical, list):
        errors.append("critical_item_indices must be a list")
    else:
        if len(set(critical)) != len(critical):
            errors.append("duplicate critical indices")
        for index in critical:
            if not isinstance(index, int) or not 0 <= index < EXPECTED_ITEMS_PER_PROFILE:
                errors.append(f"invalid critical index {index!r}")
    return errors


def monitor_pages(site: Path) -> tuple[dict[str, Path], dict[str, dict]]:
    paths: dict[str, Path] = {}
    definitions: dict[str, dict] = {}
    for page in sorted((site / "assessment-lab").glob("*/index.html")):
        source = page.read_text(encoding="utf-8")
        definition = load_definition(source)
        if definition.get("score_type") != "monitor":
            continue
        slug = str(definition.get("slug") or page.parent.name)
        if slug in paths:
            raise SystemExit(f"Duplicate monitor page slug: {slug}")
        paths[slug] = page
        definitions[slug] = definition
    return paths, definitions


def publish(site: Path, repo_root: Path | None = None) -> dict:
    site = site.resolve()
    root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    profiles, shards = load_profiles(root)
    pages, definitions = monitor_pages(site)

    if len(pages) != EXPECTED_PROFILES:
        raise SystemExit(
            f"Expected {EXPECTED_PROFILES} monitor pages, found {len(pages)}"
        )
    missing_profiles = sorted(set(pages) - set(profiles))
    extra_profiles = sorted(set(profiles) - set(pages))
    if missing_profiles or extra_profiles:
        raise SystemExit(
            {"missing_profiles": missing_profiles, "extra_profiles": extra_profiles}
        )

    validation_errors: dict[str, list[str]] = {}
    all_items: list[str] = []
    title_mismatches: list[dict] = []
    for slug, profile in sorted(profiles.items()):
        errors = validate_profile(slug, profile)
        if errors:
            validation_errors[slug] = errors
        all_items.extend(profile.get("items") or [])
        current_title = str(definitions[slug].get("title") or "")
        if current_title != profile.get("title"):
            title_mismatches.append(
                {
                    "slug": slug,
                    "definition": current_title,
                    "profile": profile.get("title"),
                }
            )

    duplicate_items = sorted(
        item for item in set(all_items) if all_items.count(item) > 1
    )
    generic_items = sorted(
        item
        for item in all_items
        if any(suffix in item for suffix in GENERIC_SUFFIXES)
    )
    if validation_errors or title_mismatches:
        raise SystemExit(
            {
                "validation_errors": validation_errors,
                "title_mismatches": title_mismatches,
            }
        )
    if len(all_items) != EXPECTED_TOTAL_ITEMS:
        raise SystemExit(
            f"Expected {EXPECTED_TOTAL_ITEMS} items, found {len(all_items)}"
        )
    if len(set(all_items)) != EXPECTED_TOTAL_ITEMS or duplicate_items:
        raise SystemExit(
            {
                "unique": len(set(all_items)),
                "duplicates": duplicate_items[:20],
            }
        )
    if generic_items:
        raise SystemExit({"generic_items": generic_items[:20]})

    changed_pages: list[str] = []
    policies: dict[str, int] = {key: 0 for key in sorted(ALLOWED_POLICIES)}
    critical_profiles: list[dict] = []
    for slug, page in sorted(pages.items()):
        profile = profiles[slug]
        source = page.read_text(encoding="utf-8")
        definition = definitions[slug]
        definition.update(
            {
                "questions": profile["items"],
                "options": profile["options"],
                "period": profile["period"],
                "summary": profile["summary"],
                "monitor_policy": profile["monitor_policy"],
                "monitor_direction": profile["monitor_direction"],
                "critical_item_indices": profile["critical_item_indices"],
                "instrument_type": "أداة متابعة أصلية غير معيارية",
                "scoring_policy": "descriptive_tracking_only",
                "item_bank_version": VERSION,
            }
        )
        updated = write_definition(source, definition)
        if updated != source:
            page.write_text(updated, encoding="utf-8")
            changed_pages.append(page.relative_to(site).as_posix())
        policies[profile["monitor_policy"]] += 1
        if profile["critical_item_indices"]:
            critical_profiles.append(
                {
                    "slug": slug,
                    "critical_item_indices": profile["critical_item_indices"],
                }
            )

    written_items: list[str] = []
    written_failures: list[dict] = []
    for slug, page in sorted(pages.items()):
        definition = load_definition(page.read_text(encoding="utf-8"))
        questions = definition.get("questions") or []
        written_items.extend(questions)
        checks = {
            "question_count": len(questions) == EXPECTED_ITEMS_PER_PROFILE,
            "options_count": len(definition.get("options") or []) == 5,
            "item_bank_version": definition.get("item_bank_version") == VERSION,
            "policy": definition.get("monitor_policy") == profiles[slug]["monitor_policy"],
            "critical_indices": definition.get("critical_item_indices")
            == profiles[slug]["critical_item_indices"],
            "scoring_policy": definition.get("scoring_policy")
            == "descriptive_tracking_only",
        }
        failed = [name for name, value in checks.items() if not value]
        if failed:
            written_failures.append({"slug": slug, "failed": failed})

    report = {
        "version": VERSION,
        "status": "passed",
        "shards": shards,
        "shard_count": len(shards),
        "monitor_pages": len(pages),
        "profiles": len(profiles),
        "items_per_profile": EXPECTED_ITEMS_PER_PROFILE,
        "total_items": len(all_items),
        "unique_items": len(set(all_items)),
        "generic_template_items": len(generic_items),
        "policies": policies,
        "critical_profiles": critical_profiles,
        "changed_pages": len(changed_pages),
        "changed_page_paths": changed_pages,
        "written_total_items": len(written_items),
        "written_unique_items": len(set(written_items)),
        "written_failures": written_failures,
        "title_mismatches": title_mismatches,
        "validation_errors": validation_errors,
    }
    if (
        written_failures
        or len(written_items) != EXPECTED_TOTAL_ITEMS
        or len(set(written_items)) != EXPECTED_TOTAL_ITEMS
    ):
        report["status"] = "failed"

    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "monitor-items-v32.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if report["status"] != "passed":
        raise SystemExit(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(publish(args.site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
