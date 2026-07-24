#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEED_DIR = ROOT / "content" / "authorized-course-feeds"
PROVIDER_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
COURSE_ID = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
LANGUAGE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")
CURRENCY = re.compile(r"^[A-Z]{3}$")
DELIVERY_MODES = {"online", "in_person", "hybrid", "self_paced"}
COURSE_STATUSES = {"scheduled", "open", "closed", "archived"}


def generated_at() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).date().isoformat()
    return datetime.now(timezone.utc).date().isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_https(value: object, field: str) -> str:
    text = str(value or "").strip()
    parsed = urlparse(text)
    require(parsed.scheme == "https" and bool(parsed.netloc), f"{field}:https_url_required")
    return text


def parse_date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError(f"{field}:invalid_date") from error


def parse_datetime(value: object, field: str) -> str:
    text = str(value or "").strip()
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field}:invalid_datetime") from error
    return text


def validate_provider(provider: object, source: str) -> dict[str, str]:
    require(isinstance(provider, dict), f"{source}:provider_object_required")
    provider_id = str(provider.get("id", "")).strip()
    name = str(provider.get("name", "")).strip()
    require(bool(PROVIDER_ID.fullmatch(provider_id)), f"{source}:provider.id_invalid")
    require(2 <= len(name) <= 160, f"{source}:provider.name_invalid")
    website = require_https(provider.get("website"), f"{source}:provider.website")
    return {"id": provider_id, "name": name, "website": website}


def validate_authorization(authorization: object, source: str, today: date) -> dict[str, object]:
    require(isinstance(authorization, dict), f"{source}:authorization_object_required")
    require(authorization.get("status") == "authorized", f"{source}:authorization.status_invalid")
    evidence_url = require_https(authorization.get("evidenceUrl"), f"{source}:authorization.evidenceUrl")
    license_name = str(authorization.get("license", "")).strip()
    require(2 <= len(license_name) <= 200, f"{source}:authorization.license_invalid")
    verified_at = parse_date(authorization.get("verifiedAt"), f"{source}:authorization.verifiedAt")
    require(verified_at <= today, f"{source}:authorization.verifiedAt_future")
    expires_raw = authorization.get("expiresAt")
    expires_at = None
    if expires_raw not in (None, ""):
        expires_at = parse_date(expires_raw, f"{source}:authorization.expiresAt")
        require(expires_at >= today, f"{source}:authorization.expired")
    return {
        "status": "authorized",
        "evidenceUrl": evidence_url,
        "license": license_name,
        "verifiedAt": verified_at.isoformat(),
        "expiresAt": expires_at.isoformat() if expires_at else None,
    }


def validate_course(course: object, source: str, provider: dict[str, str]) -> dict[str, object]:
    require(isinstance(course, dict), f"{source}:course_object_required")
    course_id = str(course.get("id", "")).strip()
    title = str(course.get("title", "")).strip()
    language = str(course.get("language", "")).strip()
    delivery = str(course.get("deliveryMode", "")).strip()
    status = str(course.get("status", "")).strip()
    require(bool(COURSE_ID.fullmatch(course_id)), f"{source}:{course_id or 'course'}.id_invalid")
    require(3 <= len(title) <= 220, f"{source}:{course_id}.title_invalid")
    require(bool(LANGUAGE.fullmatch(language)), f"{source}:{course_id}.language_invalid")
    require(delivery in DELIVERY_MODES, f"{source}:{course_id}.deliveryMode_invalid")
    require(status in COURSE_STATUSES, f"{source}:{course_id}.status_invalid")

    rights = course.get("rights")
    require(isinstance(rights, dict), f"{source}:{course_id}.rights_object_required")
    require(rights.get("metadataReuse") is True, f"{source}:{course_id}.metadata_reuse_not_authorized")

    normalized: dict[str, object] = {
        "id": course_id,
        "provider": provider,
        "title": title,
        "language": language,
        "canonicalUrl": require_https(course.get("canonicalUrl"), f"{source}:{course_id}.canonicalUrl"),
        "enrollmentUrl": require_https(course.get("enrollmentUrl"), f"{source}:{course_id}.enrollmentUrl"),
        "deliveryMode": delivery,
        "status": status,
        "updatedAt": parse_datetime(course.get("updatedAt"), f"{source}:{course_id}.updatedAt"),
        "rights": {
            "metadataReuse": True,
            "contentReuse": rights.get("contentReuse") is True,
            "attributionText": str(rights.get("attributionText", "")).strip(),
        },
    }

    optional_strings = {
        "summary": 1500,
        "providerName": 160,
        "duration": 120,
    }
    for field, limit in optional_strings.items():
        value = course.get(field)
        if value not in (None, ""):
            text = str(value).strip()
            require(len(text) <= limit, f"{source}:{course_id}.{field}_too_long")
            normalized[field] = text

    for field in ("imageUrl",):
        value = course.get(field)
        if value not in (None, ""):
            normalized[field] = require_https(value, f"{source}:{course_id}.{field}")

    for field, limit in (("instructors", 50), ("categories", 30), ("audience", 20)):
        value = course.get(field)
        if value is not None:
            require(isinstance(value, list) and len(value) <= limit, f"{source}:{course_id}.{field}_invalid")
            normalized[field] = [str(item).strip() for item in value if str(item).strip()]

    price = course.get("price")
    currency = course.get("currency")
    if price is not None:
        require(isinstance(price, (int, float)) and not isinstance(price, bool) and price >= 0, f"{source}:{course_id}.price_invalid")
        require(bool(CURRENCY.fullmatch(str(currency or ""))), f"{source}:{course_id}.currency_invalid")
        normalized["price"] = price
        normalized["currency"] = str(currency)
    elif currency not in (None, ""):
        raise ValueError(f"{source}:{course_id}.currency_without_price")

    for field in ("startsAt", "endsAt"):
        value = course.get(field)
        if value not in (None, ""):
            normalized[field] = parse_datetime(value, f"{source}:{course_id}.{field}")

    return normalized


def load_feeds(feed_dir: Path, today: date | None = None) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    today = today or date.today()
    feed_dir = Path(feed_dir)
    if not feed_dir.exists():
        return [], []

    providers: list[dict[str, object]] = []
    courses: list[dict[str, object]] = []
    provider_ids: set[str] = set()
    course_keys: set[str] = set()

    for path in sorted(feed_dir.glob("*.json")):
        source = path.name
        data = json.loads(path.read_text(encoding="utf-8"))
        require(isinstance(data, dict), f"{source}:feed_object_required")
        require(data.get("feedVersion") == "1.0", f"{source}:feedVersion_invalid")
        provider = validate_provider(data.get("provider"), source)
        authorization = validate_authorization(data.get("authorization"), source, today)
        require(provider["id"] not in provider_ids, f"{source}:duplicate_provider_id")
        provider_ids.add(provider["id"])
        providers.append({**provider, "authorization": authorization})

        raw_courses = data.get("courses")
        require(isinstance(raw_courses, list) and 1 <= len(raw_courses) <= 5000, f"{source}:courses_invalid")
        for raw_course in raw_courses:
            course = validate_course(raw_course, source, provider)
            unique_key = f'{provider["id"]}:{course["id"]}'
            require(unique_key not in course_keys, f"{source}:duplicate_course_id:{unique_key}")
            course_keys.add(unique_key)
            course["uid"] = unique_key
            course["authorization"] = authorization
            courses.append(course)

    return providers, courses


def publish(site: Path, feed_dir: Path | None = None, today: date | None = None) -> dict[str, int]:
    site = Path(site).resolve()
    require(site.is_dir(), f"missing_site:{site}")
    providers, courses = load_feeds(feed_dir or DEFAULT_FEED_DIR, today=today)
    payload = {
        "apiVersion": "1.0.0",
        "generatedAt": generated_at(),
        "totalProviders": len(providers),
        "totalCourses": len(courses),
        "integrationPolicy": {
            "authorizationRequired": True,
            "metadataOnlyByDefault": True,
            "canonicalSourceRequired": True,
            "protectedCourseContentExcluded": True,
        },
        "providers": sorted(providers, key=lambda item: str(item["id"])),
        "courses": sorted(courses, key=lambda item: str(item["uid"])),
    }
    api_dir = site / "api" / "v1"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "courses.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "version": 201,
        "providers": len(providers),
        "courses": len(courses),
    }


def main() -> None:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    result = publish(site)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
