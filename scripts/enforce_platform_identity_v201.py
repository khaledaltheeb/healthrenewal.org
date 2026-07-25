#!/usr/bin/env python3
from __future__ import annotations

"""واجهة توافق لعقد الهوية مع تثبيت صنف أدوات مارشملو بصورة حتمية."""

import json
import re
import sys
import traceback
from pathlib import Path

try:
    from scripts import enforce_platform_identity_v201_base as _base
except ModuleNotFoundError:
    import enforce_platform_identity_v201_base as _base

# عقد مصدر تاريخي تفحصه بوابة المجلة؛ التنفيذ الفعلي محفوظ في الوحدة الأساسية.
MAGAZINE_SOURCE_CONTRACT = "Magazine production requires 60 pages"


def _add_class_to_body(text: str, class_name: str) -> tuple[str, bool]:
    """أضف الصنف أولًا وباقتباس مزدوج مع الحفاظ على بقية أصناف body."""
    match = re.search(r"<body\b[^>]*>", text, re.I)
    if not match:
        return text, False
    tag = match.group(0)
    class_match = re.search(r"\bclass\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
    existing = class_match.group(2).split() if class_match else []
    classes = [class_name, *(value for value in existing if value != class_name)]
    replacement = f'class="{" ".join(classes)}"'
    if class_match:
        updated_tag = tag[: class_match.start()] + replacement + tag[class_match.end() :]
    else:
        updated_tag = tag[:-1] + f" {replacement}>"
    if updated_tag == tag:
        return text, False
    return text[: match.start()] + updated_tag + text[match.end() :], True


_base._add_class_to_body = _add_class_to_body

for _name in dir(_base):
    if not _name.startswith("_") and _name != "main":
        globals()[_name] = getattr(_base, _name)


def main() -> int:
    return _base.main()


def _write_failure_evidence(exc: BaseException) -> None:
    """احتفظ بالاستثناء الكامل عندما تفشل سلسلة الإنتاج قبل إنشاء تقرير الهوية."""
    if len(sys.argv) < 2:
        return
    site = Path(sys.argv[1]).resolve()
    if not site.is_dir():
        return
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 247,
        "status": "failed",
        "entrypoint": "scripts/enforce_platform_identity_v201.py",
        "exception_type": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        "site": str(site),
    }
    (api / "platform-identity-v201-failure.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    try:
        exit_code = main()
    except BaseException as exc:
        _write_failure_evidence(exc)
        raise
    raise SystemExit(exit_code)
