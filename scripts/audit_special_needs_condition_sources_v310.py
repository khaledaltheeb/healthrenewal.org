#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse

ROOT = Path(__file__).resolve().parents[1]
CONDITION_FILES = (
    ROOT / "content" / "v302" / "autism-ar.json",
    ROOT / "content" / "v302" / "down-syndrome-ar.json",
)
VERSION = 310
ALLOWED_LEVELS = {"S1", "S2", "S3", "S4", "S5"}
TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}
SHORTENER_HOSTS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "buff.ly"}
REVIEW_INTERVAL_DAYS = 180
MAX_REVIEW_AGE_DAYS = 730


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


def audit_condition(path: Path, today: date) -> dict[str, Any]:
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
    due_within_30: list[str] = []
    overdue: list[str] = []
    ages: list[int] = []
    review_due: dict[str, str] = {}
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
        reviewed = parse_iso_date(source["reviewed"], f"{slug}/{source_id}/reviewed")
        if reviewed > today:
            raise SystemExit(f"Source review date cannot be in the future: {slug}/{source_id}/{reviewed}")
        age = (today - reviewed).days
        if age > MAX_REVIEW_AGE_DAYS:
            raise SystemExit(f"Source review is too old for publication: {slug}/{source_id}/{age} days")
        ages.append(age)
        due = reviewed + timedelta(days=REVIEW_INTERVAL_DAYS)
        review_due[source_id] = due.isoformat()
        if due < today:
            overdue.append(source_id)
        elif (due - today).days <= 30:
            due_within_30.append(source_id)
        source_rows.append(
            {
                "id": source_id,
                "host": host,
                "level": level,
                "reviewed": reviewed.isoformat(),
                "next_review_due": due.isoformat(),
                "query_parameter_count": len(parameters),
            }
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
        "maximum_review_age_days": max(ages),
        "overdue_source_ids": sorted(overdue),
        "due_within_30_days": sorted(due_within_30),
        "source_usage": dict(sorted(usage.items())),
        "sources": source_rows,
    }


def audit(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    conditions = [audit_condition(path, today) for path in CONDITION_FILES]
    all_rows = [row for condition in conditions for row in condition["sources"]]
    hosts = {row["host"] for row in all_rows}
    return {
        "version": VERSION,
        "status": "passed",
        "checked_at": today.isoformat(),
        "review_interval_days": REVIEW_INTERVAL_DAYS,
        "maximum_allowed_review_age_days": MAX_REVIEW_AGE_DAYS,
        "condition_count": len(conditions),
        "condition_slugs": [condition["slug"] for condition in conditions],
        "source_count": sum(condition["source_count"] for condition in conditions),
        "distinct_host_count": len(hosts),
        "overdue_source_count": sum(len(condition["overdue_source_ids"]) for condition in conditions),
        "due_within_30_days_count": sum(len(condition["due_within_30_days"]) for condition in conditions),
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
