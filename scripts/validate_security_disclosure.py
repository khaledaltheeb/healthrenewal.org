#!/usr/bin/env python3
"""Validate the repository vulnerability-disclosure contract."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SECURITY = ROOT / "SECURITY.md"
SECURITY_TXT = ROOT / ".well-known" / "security.txt"
CONTACT_FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "security-contact.yml"
REGISTER = ROOT / "docs" / "innovation-register.md"

ADVISORY_URL = "https://github.com/khaledaltheeb/pterminology-site/security/advisories/new"
FALLBACK_URL = "https://github.com/khaledaltheeb/pterminology-site/issues/new?template=security-contact.yml"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def parse_security_txt(text: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            fail(f"security.txt line {number} is not a field")
        name, value = line.split(":", 1)
        name, value = name.strip(), value.strip()
        if not name or not value:
            fail(f"security.txt line {number} has an empty name or value")
        fields.setdefault(name, []).append(value)
    return fields


def require_https(value: str, field: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        fail(f"{field} must be an HTTPS URL without embedded credentials: {value}")


def main() -> None:
    for path in (SECURITY, SECURITY_TXT, CONTACT_FORM, REGISTER):
        if not path.is_file():
            fail(f"missing required file: {path.relative_to(ROOT)}")

    policy = SECURITY.read_text(encoding="utf-8")
    required_policy_terms = (
        "Private vulnerability reporting",
        "لا تنشر",
        "public Issues",
        "health data",
        "No bounty",
        FALLBACK_URL,
    )
    for term in required_policy_terms:
        if term not in policy:
            fail(f"SECURITY.md is missing required policy language: {term}")

    fields = parse_security_txt(SECURITY_TXT.read_text(encoding="utf-8"))
    for required in ("Contact", "Expires", "Preferred-Languages", "Canonical", "Policy"):
        if required not in fields:
            fail(f"security.txt is missing {required}")

    contacts = fields["Contact"]
    if len(contacts) != 2 or set(contacts) != {ADVISORY_URL, FALLBACK_URL}:
        fail("security.txt must contain exactly the private advisory and safe fallback contacts")

    for field in ("Contact", "Canonical", "Policy"):
        for value in fields.get(field, []):
            require_https(value, field)

    try:
        expires = datetime.fromisoformat(fields["Expires"][0].replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"Expires is not ISO-8601: {exc}")
    if expires.tzinfo is None:
        fail("Expires must include a timezone")
    now = datetime.now(timezone.utc)
    remaining_days = (expires.astimezone(timezone.utc) - now).total_seconds() / 86400
    if remaining_days <= 0:
        fail("security.txt has expired")
    if remaining_days > 366:
        fail("security.txt expiration exceeds the one-year maintenance window")

    languages = ",".join(fields["Preferred-Languages"])
    if "ar" not in languages or "en" not in languages:
        fail("Preferred-Languages must include ar and en")

    form = CONTACT_FORM.read_text(encoding="utf-8")
    required_form_terms = (
        "هذا الطلب عام",
        "This request is public",
        "لا تكتب تفاصيل الثغرة",
        "Do not include vulnerability details",
        "required: true",
    )
    for term in required_form_terms:
        if term not in form:
            fail(f"security contact form is missing safeguard: {term}")
    forbidden_form_terms = ("email:", "phone:", "access token", "reproduction steps")
    lowered_form = form.lower()
    for term in forbidden_form_terms:
        if term in lowered_form:
            fail(f"public contact form must not solicit sensitive details: {term}")

    register = REGISTER.read_text(encoding="utf-8")
    for term in ("الفائدة", "الدليل", "الأمان", "القابلية للتنفيذ", "التكلفة التقنية", "المخاطر"):
        if term not in register:
            fail(f"innovation register is missing ranking dimension: {term}")
    if "GitHub Pages" not in register or "RFC 9116" not in register:
        fail("innovation register must disclose the project-site discovery limitation")

    print("Security disclosure contract passed")
    print(f"Expires in approximately {remaining_days:.1f} days")


if __name__ == "__main__":
    main()
