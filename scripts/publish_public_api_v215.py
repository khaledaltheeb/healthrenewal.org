from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import import_authorized_courses_v215 as _importer
from scripts import publish_public_api_v215_core as _core
from scripts.publish_public_api_v215_core import *  # noqa: F401,F403

SECURITY_CONTRACT_VERSION = 218
DISCOVERY_CONTRACT_VERSION = 229
HOME_LINK_MARKER = 'data-developers-discovery-v229'
_core_validate_courses = _core.validate_courses
_core_course_schema = _core.course_schema
_ACTIVE_SOURCE_EXPIRY: dict[str, str | None] = {}


def public_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    _ACTIVE_SOURCE_EXPIRY.clear()
    for raw in manifest.get("sources") or []:
        if not isinstance(raw, dict) or not raw.get("enabled"):
            continue
        try:
            source = _importer.validate_source(raw)
        except _importer.CourseImportError as exc:
            raise PublicApiError(f"inactive or invalid course source: {exc}") from exc
        _ACTIVE_SOURCE_EXPIRY[source.source_id] = source.permission_expires_at
        result.append(
            {
                "id": source.source_id,
                "provider": source.provider,
                "license_url": source.license_url,
                "permission_status": "approved",
                "permission_duration": source.permission_duration,
                "permission_expires_at": source.permission_expires_at,
                "allowed_actions": sorted(set(raw.get("allowed_actions") or [])),
            }
        )
    return sorted(result, key=lambda item: str(item.get("id") or ""))


def validate_courses(
    imported: dict[str, Any],
    approved_ids: set[str],
) -> list[dict[str, Any]]:
    courses = _core_validate_courses(imported, approved_ids)
    for item in courses:
        source_id = str(item.get("source_id") or "")
        if source_id not in _ACTIVE_SOURCE_EXPIRY:
            raise PublicApiError(
                "published course source permission was not revalidated in this publication run"
            )
        if "permission_expires_at" not in item:
            raise PublicApiError(
                "published course is missing permission_expires_at from security contract v218"
            )
        expires_at = item.get("permission_expires_at")
        expected_expiry = _ACTIVE_SOURCE_EXPIRY[source_id]
        if expires_at != expected_expiry:
            raise PublicApiError(
                "published course permission window does not match its active source permission"
            )
        if expires_at in {None, ""}:
            continue
        try:
            expiry = date.fromisoformat(str(expires_at))
        except ValueError as exc:
            raise PublicApiError("published course has invalid permission_expires_at") from exc
        if expiry < date.today():
            raise PublicApiError("published course permission has expired")
    return courses


def course_schema() -> dict[str, Any]:
    schema = _core_course_schema()
    properties = schema.setdefault("properties", {})
    properties["permission_expires_at"] = {
        "type": ["string", "null"],
        "format": "date",
        "description": "Expiry date for fixed permission, or null for perpetual permission.",
    }
    required = schema.setdefault("required", [])
    if "permission_expires_at" not in required:
        required.append("permission_expires_at")
    return schema


def ensure_homepage_developers_link(site: Path) -> bool:
    homepage = site / "index.html"
    if not homepage.is_file():
        return False
    text = homepage.read_text(encoding="utf-8")
    if HOME_LINK_MARKER in text:
        return False
    anchor = (
        f'<a href="developers/" {HOME_LINK_MARKER}>'
        "واجهة المطورين والتكامل</a>"
    )

    # The institutional homepage may use a semantic nav, div, or another
    # suitable container. Discovery must depend on the stable class contract,
    # not on one historical HTML tag.
    match = re.search(
        r'<(?P<tag>[a-zA-Z][\w:-]*)\b(?P<attrs>[^>]*\bclass="[^"]*\bfooter-links\b[^"]*"[^>]*)>',
        text,
        flags=re.I,
    )
    if not match:
        raise PublicApiError("homepage footer links container is missing")
    opening = match.group(0)
    text = text[: match.end()] + anchor + text[match.end() :]
    homepage.write_text(text, encoding="utf-8")
    return True


def homepage_developers_link_present(site: Path) -> bool:
    homepage = site / "index.html"
    return homepage.is_file() and HOME_LINK_MARKER in homepage.read_text(encoding="utf-8")


_core.public_sources = public_sources
_core.validate_courses = validate_courses
_core.course_schema = course_schema


def publish(
    site: Path = SITE,
    manifest_path: Path = SOURCE_MANIFEST,
    import_path: Path | None = None,
) -> dict[str, Any]:
    target = Path(site).resolve()
    report = _core.publish(
        site=target,
        manifest_path=manifest_path,
        import_path=import_path,
    )
    homepage_link_added = ensure_homepage_developers_link(target)
    report["security_contract_version"] = SECURITY_CONTRACT_VERSION
    report["permission_expiry_revalidated"] = True
    report["course_source_windows_matched"] = True
    report["discovery_contract_version"] = DISCOVERY_CONTRACT_VERSION
    report["developers_homepage_link_added"] = homepage_link_added
    report["developers_homepage_link_present"] = homepage_developers_link_present(target)
    report_path = ROOT / ".build" / "reports" / "public-api-v215.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    print(json.dumps(publish(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
