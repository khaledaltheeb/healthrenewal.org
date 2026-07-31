#!/usr/bin/env python3
"""Validate the public accessibility-barrier GitHub Issue Form.

The contract intentionally permits only a small, reviewed set of technical
fields. It prevents the form from drifting into collecting health, identity,
contact, authentication, or private-document data in a public issue.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

FORM_PATH = Path(".github/ISSUE_TEMPLATE/accessibility-barrier.yml")
STATEMENT_URL = "https://healthrenewal.org/accessibility/"
PUBLIC_SITE_PREFIX = "https://healthrenewal.org/"

EXPECTED_FIELDS = {
    "page_url": ("input", True),
    "barrier_type": ("dropdown", True),
    "observed": ("textarea", True),
    "expected": ("textarea", True),
    "environment": ("input", False),
    "impact": ("dropdown", True),
    "workaround": ("textarea", False),
    "privacy": ("checkboxes", False),
}

REQUIRED_BARRIER_OPTIONS = {
    "التنقل بلوحة المفاتيح أو مؤشر التركيز",
    "قارئ الشاشة أو البنية الدلالية",
    "التباين أو الألوان",
    "التكبير أو إعادة تدفق المحتوى",
    "الهاتف أو اتجاه RTL",
    "الحركة أو الوميض",
    "نموذج أو عنصر تفاعلي",
    "نص مخفي أو مقطوع",
    "صورة أو بديل نصي",
    "فيديو أو صوت أو تفريغ نصي",
    "لغة أو وضوح المحتوى",
    "أخرى",
}

REQUIRED_IMPACT_OPTIONS = {
    "يمنع إكمال المهمة بالكامل",
    "يجعل المهمة صعبة جدًا",
    "يسبب ارتباكًا أو جهدًا إضافيًا",
    "ملاحظة تحسين عامة",
}

FORBIDDEN_FIELD_ID_PARTS = {
    "name",
    "email",
    "phone",
    "address",
    "identity",
    "id_number",
    "medical",
    "diagnosis",
    "license",
    "password",
    "token",
    "secret",
    "attachment",
    "document",
}

FORBIDDEN_COLLECTION_LABEL_PATTERNS = (
    re.compile(r"(?:الاسم|اسمك|البريد|الهاتف|العنوان|رقم الهوية|رقم الترخيص|التشخيص|السجل الطبي|الملف الطبي)\s*(?:\*|:|$)", re.IGNORECASE),
    re.compile(r"\b(?:password|access token|secret|medical record|diagnosis|email address|phone number)\b", re.IGNORECASE),
)

FORBIDDEN_UPLOAD_REQUESTS = (
    "أرفق",
    "ارفق",
    "ارفع ملف",
    "حمّل وثيقة",
    "upload a file",
    "attach a document",
    "attach a screenshot containing",
)


@dataclass(frozen=True)
class Field:
    field_type: str
    field_id: str
    block: str
    label: str
    required: bool


def split_blocks(text: str) -> list[str]:
    marker = "\n  - type: "
    return [part for part in text.split(marker)[1:]]


def extract_scalar(block: str, key: str) -> str:
    match = re.search(rf"(?m)^\s{{4,}}{re.escape(key)}:\s*(.+?)\s*$", block)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def parse_fields(text: str, errors: list[str]) -> list[Field]:
    fields: list[Field] = []
    for block in split_blocks(text):
        first_line, _, rest = block.partition("\n")
        field_type = first_line.strip()
        field_id = extract_scalar(rest, "id")
        if not field_id:
            if field_type != "markdown":
                errors.append(f"interactive block of type {field_type!r} is missing an id")
            continue
        label = extract_scalar(rest, "label")
        required = bool(re.search(r"(?m)^\s{4}validations:\s*$[\s\S]*?^\s{6}required:\s*true\s*$", rest))
        fields.append(Field(field_type, field_id, block, label, required))
    return fields


def block_options(block: str) -> set[str]:
    return {
        match.group(1).strip().strip('"').strip("'")
        for match in re.finditer(r"(?m)^\s{8}-\s+(.+?)\s*$", block)
    }


def validate_text(text: str) -> list[str]:
    errors: list[str] = []

    required_header_fragments = (
        "name: الإبلاغ عن عائق في الإتاحة",
        "description: أبلغ عن مشكلة",
        'title: "[إتاحة]: "',
        "labels:\n  - accessibility",
    )
    for fragment in required_header_fragments:
        if fragment not in text:
            errors.append(f"missing issue-form header contract: {fragment}")

    if STATEMENT_URL not in text:
        errors.append("the form must link to the public accessibility statement")
    if "هذا البلاغ **عام**" not in text and "هذا البلاغ عام" not in text:
        errors.append("the opening warning must state that the issue is public")
    for fragment in ("كلمات مرور", "رموز دخول", "معلومات صحية", "بيانات تعريفية", "وثائق"):
        if fragment not in text:
            errors.append(f"privacy warning missing prohibited-data category: {fragment}")

    lowered = text.casefold()
    for phrase in FORBIDDEN_UPLOAD_REQUESTS:
        if phrase.casefold() in lowered:
            errors.append(f"unsafe upload request detected: {phrase}")

    fields = parse_fields(text, errors)
    ids = [field.field_id for field in fields]
    if len(ids) != len(set(ids)):
        duplicates = sorted({field_id for field_id in ids if ids.count(field_id) > 1})
        errors.append(f"duplicate issue-form field IDs: {duplicates}")

    actual_ids = set(ids)
    expected_ids = set(EXPECTED_FIELDS)
    missing = sorted(expected_ids - actual_ids)
    unexpected = sorted(actual_ids - expected_ids)
    if missing:
        errors.append(f"missing governed fields: {missing}")
    if unexpected:
        errors.append(f"unexpected public data-collection fields: {unexpected}")

    # Sensitive identifiers and labels must be rejected even when the field is
    # already unexpected. This produces an explicit safety signal in addition
    # to the allow-list failure.
    for field in fields:
        normalized_id = field.field_id.casefold()
        if any(part in normalized_id for part in FORBIDDEN_FIELD_ID_PARTS):
            errors.append(f"sensitive field identifier is not allowed in a public issue: {field.field_id}")
        for pattern in FORBIDDEN_COLLECTION_LABEL_PATTERNS:
            if pattern.search(field.label):
                errors.append(f"sensitive collection label is not allowed: {field.label}")

    by_id = {field.field_id: field for field in fields}
    for field_id, (expected_type, must_be_required) in EXPECTED_FIELDS.items():
        field = by_id.get(field_id)
        if not field:
            continue
        if field.field_type != expected_type:
            errors.append(f"{field_id} must use type {expected_type}, found {field.field_type}")
        if must_be_required and not field.required:
            errors.append(f"{field_id} must be required")
        if not field.label:
            errors.append(f"{field_id} must have a visible label")

    page_field = by_id.get("page_url")
    if page_field:
        if PUBLIC_SITE_PREFIX not in page_field.block:
            errors.append("page_url must show the platform's public URL prefix")
        placeholder_match = re.search(r"(?m)^\s{6}placeholder:\s*(.+?)\s*$", page_field.block)
        placeholder = placeholder_match.group(1).strip() if placeholder_match else ""
        if not placeholder.startswith(PUBLIC_SITE_PREFIX):
            errors.append("page_url placeholder must use the public platform origin")
        if "?" in placeholder or "#" in placeholder:
            errors.append("page_url placeholder must not encourage query strings or fragments")
        if "رموز دخول" not in page_field.block or "بيانات خاصة" not in page_field.block:
            errors.append("page_url description must warn against secrets and private data")

    barrier_field = by_id.get("barrier_type")
    if barrier_field:
        options = block_options(barrier_field.block)
        missing_options = sorted(REQUIRED_BARRIER_OPTIONS - options)
        if missing_options:
            errors.append(f"barrier_type is missing reviewed options: {missing_options}")
        if len(options) != len(REQUIRED_BARRIER_OPTIONS):
            extras = sorted(options - REQUIRED_BARRIER_OPTIONS)
            if extras:
                errors.append(f"barrier_type has unreviewed options: {extras}")

    impact_field = by_id.get("impact")
    if impact_field:
        options = block_options(impact_field.block)
        missing_options = sorted(REQUIRED_IMPACT_OPTIONS - options)
        if missing_options:
            errors.append(f"impact is missing reviewed options: {missing_options}")
        extras = sorted(options - REQUIRED_IMPACT_OPTIONS)
        if extras:
            errors.append(f"impact has unreviewed options: {extras}")

    privacy_field = by_id.get("privacy")
    if privacy_field:
        if privacy_field.block.count("required: true") < 2:
            errors.append("both privacy acknowledgements must be mandatory")
        required_privacy_fragments = (
            "لا يتضمن كلمات مرور أو رموز دخول أو معلومات صحية أو بيانات تعريفية أو وثائق خاصة",
            "البلاغ عام وقد يظهر للزوار ومحركات البحث",
        )
        for fragment in required_privacy_fragments:
            if fragment not in privacy_field.block:
                errors.append(f"privacy acknowledgement missing: {fragment}")

    if "screenshots" in lowered or "لقطة شاشة" in text:
        errors.append("the public form must not request screenshots; they can expose private data")

    return errors


def validate_file(root: Path) -> list[str]:
    path = root / FORM_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"missing {FORM_PATH}"]
    return validate_text(text)


def assert_rejected(text: str, expected_fragment: str, label: str) -> None:
    errors = validate_text(text)
    if not any(expected_fragment in error for error in errors):
        joined = "\n".join(errors) or "no errors"
        raise AssertionError(f"self-test did not reject {label}; got:\n{joined}")


def run_self_test(root: Path) -> int:
    path = root / FORM_PATH
    try:
        good = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"self-test requires {FORM_PATH}", file=sys.stderr)
        return 1

    good_errors = validate_text(good)
    if good_errors:
        print("valid form failed self-test:", file=sys.stderr)
        for error in good_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    try:
        missing_required = good.replace(
            "id: page_url\n    attributes:",
            "id: page_url\n    validations:\n      required: false\n    attributes:",
            1,
        ).replace(
            "    validations:\n      required: true\n\n  - type: dropdown\n    id: barrier_type",
            "\n  - type: dropdown\n    id: barrier_type",
            1,
        )
        assert_rejected(missing_required, "page_url must be required", "optional page URL")

        extra_sensitive = good + """

  - type: input
    id: medical_record
    attributes:
      label: رقم الملف الطبي
"""
        assert_rejected(extra_sensitive, "unexpected public data-collection fields", "medical record field")
        assert_rejected(extra_sensitive, "sensitive field identifier", "sensitive field ID")
        assert_rejected(extra_sensitive, "sensitive collection label", "sensitive field label")

        unsafe_upload = good.replace(
            "اذكر المشكلة التقنية فقط.",
            "اذكر المشكلة التقنية فقط. أرفق وثيقة توضح المشكلة.",
            1,
        )
        assert_rejected(unsafe_upload, "unsafe upload request", "document upload request")

        missing_public = good.replace("هذا البلاغ **عام**", "هذا البلاغ", 1)
        assert_rejected(missing_public, "must state that the issue is public", "missing public warning")

        duplicate_id = good.replace("id: environment", "id: observed", 1)
        assert_rejected(duplicate_id, "duplicate issue-form field IDs", "duplicate field ID")

        external_placeholder = good.replace(
            "placeholder: https://healthrenewal.org/...",
            "placeholder: https://example.com/private?token=123",
            1,
        )
        assert_rejected(external_placeholder, "placeholder must use the public platform origin", "external placeholder")
    except AssertionError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    # Ensure the self-test does not depend on writing into the repository.
    with tempfile.TemporaryDirectory() as directory:
        mirror = Path(directory) / FORM_PATH
        mirror.parent.mkdir(parents=True)
        mirror.write_text(good, encoding="utf-8")
        if validate_file(Path(directory)):
            print("temporary fixture validation failed", file=sys.stderr)
            return 1

    print("accessibility feedback validator self-test: passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    if args.self_test:
        return run_self_test(root)

    errors = validate_file(root)
    if errors:
        print("accessibility feedback contract validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("accessibility feedback contract: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
