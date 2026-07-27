#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse

ROOT = Path(__file__).resolve().parents[1]
CONDITION_FILES = (
    ROOT / "content" / "v302" / "autism-ar.json",
    ROOT / "content" / "v302" / "down-syndrome-ar.json",
)
MAINTENANCE = ROOT / "content" / "v310" / "special-needs-condition-source-maintenance-ar.json"
VERSION = 310
ALLOWED_LEVELS = {"S1", "S2", "S3", "S4", "S5"}
TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
SHORTENER_HOSTS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "buff.ly"}
MAX_METADATA_CHECK_AGE_DAYS = 365


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON object required: {path}")
    return payload


def parse_iso_date(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise SystemExit(f"Invalid ISO date for {label}: {value}") from exc


def validate_url(value: Any, source_id: str) -> tuple[str, tuple[str, ...]]:
    parsed = urlparse(str(value))
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit(f"Source URL must use HTTPS: {source_id}/{value}")
    host = parsed.netloc.lower().split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    if host in SHORTENER_HOSTS:
        raise SystemExit(f"URL shorteners are not permitted in scientific sources: {source_id}/{host}")
    parameters = tuple(sorted(key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)))
    tracking = [key for key in parameters if key.startswith("utm_") or key in TRACKING_PARAMETERS]
    if tracking:
        raise SystemExit(f"Tracking parameters are not permitted in source URLs: {source_id}/{tracking}")
    return host, parameters


def load_maintenance(today: date) -> dict[str, Any]:
    data = read_json(MAINTENANCE)
    if data.get("version") != VERSION or data.get("language") != "ar":
        raise SystemExit("Source maintenance manifest contract failed")
    if data.get("check_scope") != "metadata-url-citation-mapping":
        raise SystemExit("Source maintenance scope must remain explicit")
    if data.get("external_http_status_check_completed") is not False:
        raise SystemExit("Do not claim a live HTTP check without a dedicated network audit")
    checked_at = parse_iso_date(data.get("checked_at"), "maintenance/checked_at")
    next_due = parse_iso_date(data.get("next_check_due"), "maintenance/next_check_due")
    if checked_at > today or next_due <= checked_at:
        raise SystemExit("Source maintenance dates are invalid")
    check_age = (today - checked_at).days
    if check_age > MAX_METADATA_CHECK_AGE_DAYS:
        raise SystemExit(f"Condition source metadata check is too old: {check_age} days")
    conditions = data.get("conditions")
    if not isinstance(conditions, dict) or set(conditions) != {"autism", "down-syndrome"}:
        raise SystemExit("Source maintenance manifest must cover both conditions")
    ids_by_slug: dict[str, set[str]] = {}
    all_ids: set[str] = set()
    for slug, item in conditions.items():
        source_ids = item.get("source_ids") if isinstance(item, dict) else None
        if not isinstance(source_ids, list) or not source_ids:
            raise SystemExit(f"Maintenance source ids are missing: {slug}")
        normalized = {str(source_id) for source_id in source_ids}
        if len(normalized) != len(source_ids):
            raise SystemExit(f"Duplicate maintenance source id: {slug}")
        overlap = all_ids.intersection(normalized)
        if overlap:
            raise SystemExit(f"Source ids cannot appear under both conditions: {sorted(overlap)}")
        all_ids.update(normalized)
        ids_by_slug[slug] = normalized
    return {
        "checked_at": checked_at,
        "next_due": next_due,
        "check_age_days": check_age,
        "maintenance_overdue": today > next_due,
        "due_within_30_days": 0 <= (next_due - today).days <= 30,
        "ids_by_slug": ids_by_slug,
        "external_http_status_check_completed": False,
        "source_file": MAINTENANCE.relative_to(ROOT).as_posix(),
    }


def audit_condition(
    path: Path,
    today: date,
    maintenance_ids: set[str],
    checked_at: date,
    next_due: date,
) -> dict[str, Any]:
    data = read_json(path)
    slug = str(data.get("slug", "")).strip()
    if slug not in {"autism", "down-syndrome"}:
        raise SystemExit(f"Unexpected condition slug: {path}/{slug}")
    prefix = "A" if slug == "autism" else "D"
    sources = data.get("sources")
    sections = data.get("sections")
    if not isinstance(sources, list) or len(sources) < 5 or not isinstance(sections, list):
        raise SystemExit(f"Condition source or section contract failed: {slug}")

    ids: set[str] = set()
    urls: set[str] = set()
    hosts: set[str] = set()
    source_ages: list[int] = []
    level_counts: Counter[str] = Counter()
    source_rows: list[dict[str, Any]] = []

    for source in sources:
        if not isinstance(source, dict):
            raise SystemExit(f"Source entries must be objects: {slug}")
        source_id = str(source.get("id", "")).strip()
        required = ("id", "organization", "title", "url", "level", "reviewed")
        missing = [key for key in required if not str(source.get(key, "")).strip()]
        if missing:
            raise SystemExit(f"Source metadata is incomplete: {slug}/{source_id}/{missing}")
        if not source_id.startswith(prefix) or not source_id[len(prefix) :].isdigit():
            raise SystemExit(f"Source id does not match the condition prefix: {slug}/{source_id}")
        if source_id in ids:
            raise SystemExit(f"Duplicate source id: {slug}/{source_id}")
        ids.add(source_id)
        url = str(source["url"])
        if url in urls:
            raise SystemExit(f"Duplicate source URL inside condition: {slug}/{url}")
        urls.add(url)
        host, parameters = validate_url(url, source_id)
        hosts.add(host)
        level = str(source["level"])
        if level not in ALLOWED_LEVELS:
            raise SystemExit(f"Invalid evidence level: {slug}/{source_id}/{level}")
        level_counts[level] += 1
        source_date = parse_iso_date(source["reviewed"], f"{slug}/{source_id}/source-date")
        if source_date > today:
            raise SystemExit(f"Source publication or guideline date cannot be in the future: {slug}/{source_id}/{source_date}")
        source_ages.append((today - source_date).days)
        source_rows.append(
            {
                "id": source_id,
                "host": host,
                "level": level,
                "source_date": source_date.isoformat(),
                "metadata_checked_at": checked_at.isoformat(),
                "next_metadata_check_due": next_due.isoformat(),
                "query_parameter_count": len(parameters),
            }
        )

    if ids != maintenance_ids:
        raise SystemExit(
            f"Maintenance manifest and condition source ids differ: {slug}/"
            f"missing={sorted(ids - maintenance_ids)}/unknown={sorted(maintenance_ids - ids)}"
        )
    if len(hosts) < 3:
        raise SystemExit(f"Condition sources need domain diversity: {slug}/{sorted(hosts)}")

    usage: Counter[str] = Counter()
    for section in sections:
        if not isinstance(section, dict):
            raise SystemExit(f"Sections must be objects: {slug}")
        refs = section.get("source_ids")
        if not isinstance(refs, list) or not refs:
            raise SystemExit(f"Every section must cite at least one source: {slug}/{section.get('id')}")
        unknown = [source_id for source_id in refs if source_id not in ids]
        if unknown:
            raise SystemExit(f"Section cites unknown sources: {slug}/{section.get('id')}/{unknown}")
        usage.update(str(source_id) for source_id in refs)
    unused = sorted(ids - set(usage))
    if unused:
        raise SystemExit(f"Unused scientific sources must be removed or cited: {slug}/{unused}")

    return {
        "slug": slug,
        "source_file": path.relative_to(ROOT).as_posix(),
        "source_count": len(sources),
        "section_count": len(sections),
        "distinct_host_count": len(hosts),
        "hosts": sorted(hosts),
        "level_counts": dict(sorted(level_counts.items())),
        "maximum_source_age_days": max(source_ages),
        "metadata_checked_at": checked_at.isoformat(),
        "next_metadata_check_due": next_due.isoformat(),
        "source_usage": dict(sorted(usage.items())),
        "sources": source_rows,
    }


def audit(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    maintenance = load_maintenance(today)
    conditions = []
    for path in CONDITION_FILES:
        raw = read_json(path)
        slug = str(raw.get("slug", "")).strip()
        conditions.append(
            audit_condition(
                path,
                today,
                maintenance["ids_by_slug"].get(slug, set()),
                maintenance["checked_at"],
                maintenance["next_due"],
            )
        )
    all_rows = [row for condition in conditions for row in condition["sources"]]
    hosts = {row["host"] for row in all_rows}
    source_count = sum(condition["source_count"] for condition in conditions)
    interval_days = (maintenance["next_due"] - maintenance["checked_at"]).days
    return {
        "version": VERSION,
        "status": "passed",
        "checked_at": today.isoformat(),
        "metadata_checked_at": maintenance["checked_at"].isoformat(),
        "next_metadata_check_due": maintenance["next_due"].isoformat(),
        "metadata_check_age_days": maintenance["check_age_days"],
        "maximum_allowed_metadata_check_age_days": MAX_METADATA_CHECK_AGE_DAYS,
        "maintenance_overdue": maintenance["maintenance_overdue"],
        "due_within_30_days": maintenance["due_within_30_days"],
        "external_http_status_check_completed": maintenance["external_http_status_check_completed"],
        "maintenance_source": maintenance["source_file"],
        "condition_count": len(conditions),
        "condition_slugs": [condition["slug"] for condition in conditions],
        "source_count": source_count,
        "distinct_host_count": len(hosts),
        "maximum_source_age_days": max(condition["maximum_source_age_days"] for condition in conditions),
        "review_interval_days": interval_days,
        "maximum_allowed_review_age_days": MAX_METADATA_CHECK_AGE_DAYS,
        "overdue_source_count": source_count if maintenance["maintenance_overdue"] else 0,
        "due_within_30_days_count": source_count if maintenance["due_within_30_days"] else 0,
        "compatibility_note": "The review-age compatibility fields refer to platform metadata checks, not source publication age.",
        "conditions": conditions,
    }


def publish(site: Path, today: date | None = None) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    report = audit(today=today)
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-condition-source-maintenance-v310.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
