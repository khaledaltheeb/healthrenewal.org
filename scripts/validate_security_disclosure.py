#!/usr/bin/env python3
"""Validate the repository vulnerability-disclosure contract."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SECURITY = ROOT / "SECURITY.md"
WELL_KNOWN_SECURITY_TXT = ROOT / ".well-known" / "security.txt"
ROOT_SECURITY_TXT = ROOT / "security.txt"
CONTACT_FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "security-contact.yml"
REGISTER = ROOT / "docs" / "innovation-register.md"
GENERATOR_PART = ROOT / ".generator-v6" / "part03"

ADVISORY_URL = "https://github.com/khaledaltheeb/healthrenewal.org/security/advisories/new"
FALLBACK_URL = "https://github.com/khaledaltheeb/healthrenewal.org/issues/new?template=security-contact.yml"
WELL_KNOWN_CANONICAL = "https://healthrenewal.org/.well-known/security.txt"
ROOT_CANONICAL = "https://healthrenewal.org/security.txt"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def parse_security_txt(text: str, label: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            fail(f"{label} line {number} is not a field")
        name, value = line.split(":", 1)
        name, value = name.strip(), value.strip()
        if not name or not value:
            fail(f"{label} line {number} has an empty name or value")
        fields.setdefault(name, []).append(value)
    return fields


def require_https(value: str, field: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        fail(f"{field} must be an HTTPS URL without embedded credentials: {value}")


def validate_security_txt(text: str, label: str) -> tuple[dict[str, list[str]], float]:
    fields = parse_security_txt(text, label)
    for required in ("Contact", "Expires", "Preferred-Languages", "Canonical", "Policy"):
        if required not in fields:
            fail(f"{label} is missing {required}")

    contacts = fields["Contact"]
    if contacts != [ADVISORY_URL, FALLBACK_URL]:
        fail(f"{label} contacts must list the private advisory first and safe fallback second")

    canonicals = fields["Canonical"]
    if set(canonicals) != {WELL_KNOWN_CANONICAL, ROOT_CANONICAL} or len(canonicals) != 2:
        fail(f"{label} must list both canonical publication URLs exactly once")

    for field in ("Contact", "Canonical", "Policy"):
        for value in fields.get(field, []):
            require_https(value, f"{label} {field}")

    try:
        expires = datetime.fromisoformat(fields["Expires"][0].replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"{label} Expires is not ISO-8601: {exc}")
    if expires.tzinfo is None:
        fail(f"{label} Expires must include a timezone")
    now = datetime.now(timezone.utc)
    remaining_days = (expires.astimezone(timezone.utc) - now).total_seconds() / 86400
    if remaining_days <= 0:
        fail(f"{label} has expired")
    if remaining_days > 366:
        fail(f"{label} expiration exceeds the one-year maintenance window")

    languages = ",".join(fields["Preferred-Languages"])
    if "ar" not in languages or "en" not in languages:
        fail(f"{label} Preferred-Languages must include ar and en")

    return fields, remaining_days


def main() -> None:
    for path in (
        SECURITY,
        WELL_KNOWN_SECURITY_TXT,
        ROOT_SECURITY_TXT,
        CONTACT_FORM,
        REGISTER,
        GENERATOR_PART,
    ):
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

    well_known_text = WELL_KNOWN_SECURITY_TXT.read_text(encoding="utf-8")
    root_text = ROOT_SECURITY_TXT.read_text(encoding="utf-8")
    if well_known_text != root_text:
        fail("root security.txt must be an exact mirror of .well-known/security.txt")

    well_known_fields, remaining_days = validate_security_txt(well_known_text, ".well-known/security.txt")
    root_fields, root_remaining_days = validate_security_txt(root_text, "security.txt")
    if well_known_fields != root_fields or abs(remaining_days - root_remaining_days) > 0.001:
        fail("security.txt mirrors produced different parsed contracts")

    generator = GENERATOR_PART.read_text(encoding="utf-8")
    required_generator_terms = (
        'SECURITY_TXT=Path("security.txt").read_text(encoding="utf-8")',
        'write(".well-known/security.txt",SECURITY_TXT)',
        'write("security.txt",SECURITY_TXT)',
    )
    for term in required_generator_terms:
        if term not in generator:
            fail(f"site generator is missing security publication step: {term}")
    if "mailto:pterminology@gmail.com" in generator:
        fail("site generator still contains the obsolete hard-coded security contact")

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
    if "security.txt" not in register or "المسار الجذري" not in register:
        fail("innovation register must document the deployable root fallback")

    print("Security disclosure contract passed")
    print("Root and .well-known security.txt files are exact mirrors")
    print("Site generator publishes both machine-readable security files")
    print(f"Expires in approximately {remaining_days:.1f} days")


if __name__ == "__main__":
    main()
