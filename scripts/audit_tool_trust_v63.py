#!/usr/bin/env python3
"""Institutional trust and safety gate for interactive tools.

The audit is intentionally source-based so unsafe wording or data-transfer code is
blocked before a generated site artifact can be published. It does not assess
clinical validity and must not be presented as specialist review.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tool-trust-v63.json"

TEXT_SOURCES = {
    # The core owns the rendered Arabic guidance, privacy boundary, and next steps.
    "daily_tools_publisher": ROOT / "scripts/publish_daily_tools_v24_core.py",
    # The wrapper owns institutional SEO and schema and remains independently audited
    # for prohibited health claims.
    "daily_tools_wrapper": ROOT / "scripts/publish_daily_tools_v24.py",
    "sleep_log_publisher": ROOT / "scripts/publish_sleep_log_v49.py",
}
SCRIPT_SOURCES = {
    "sleep_log_runtime": ROOT / "assets/sleep-log-v49.js",
}

PROHIBITED_CLAIMS = {
    "diagnostic_claim": re.compile(r"(?:هذا|النتيجة|الأداة|الاختبار)\s+(?:تؤكد|تثبت|تشخّص|تشخص)\s+(?:أنك|إصابتك|الاضطراب|المرض)", re.I),
    "guaranteed_cure": re.compile(r"(?:يعالج|يشفي|يضمن الشفاء|علاج نهائي|نتيجة مضمونة)", re.I),
    "medical_replacement": re.compile(r"(?:بديل(?:ًا)?\s+عن\s+(?:الطبيب|المختص)|لا تحتاج\s+(?:طبيب|مختص))", re.I),
    "medication_advice": re.compile(r"(?:ابدأ|أوقف|زد|خفّض)\s+(?:الدواء|الجرعة)", re.I),
}
NETWORK_APIS = re.compile(r"\b(?:fetch|XMLHttpRequest|sendBeacon|WebSocket)\s*\(", re.I)

REQUIRED_MARKERS = {
    "daily_tools_publisher": {
        "local_privacy": ("لا تُرسل البيانات إلى خادم", "لا ترسل البيانات إلى خادم"),
        "non_diagnostic": ("غير تشخيص", "لا يغني عن التشخيص", "ليس تشخيص"),
        "next_step": ("متى تطلب المساعدة", "اطلب المساعدة", "مختص"),
    },
    "sleep_log_publisher": {
        "local_privacy": ("لا تُرسل البيانات إلى خادم", "لا ترسل البيانات إلى خادم"),
        "non_diagnostic": ("غير تشخيص", "ليس تشخيص"),
        "deletion": ("حذف", "امسح"),
        "next_step": ("متى تطلب المساعدة", "اطلب المساعدة", "مختص"),
    },
}


def read(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def main() -> int:
    errors: list[dict[str, str]] = []
    checks: list[dict[str, object]] = []
    texts: dict[str, str] = {}

    for name, path in {**TEXT_SOURCES, **SCRIPT_SOURCES}.items():
        try:
            texts[name] = read(path)
            checks.append({"check": "source_exists", "source": name, "passed": True})
        except FileNotFoundError as exc:
            errors.append({"source": name, "rule": "source_exists", "detail": str(exc)})

    for name, text in texts.items():
        for rule, pattern in PROHIBITED_CLAIMS.items():
            match = pattern.search(text)
            passed = match is None
            checks.append({"check": rule, "source": name, "passed": passed})
            if match:
                errors.append({"source": name, "rule": rule, "detail": match.group(0)})

    for name, requirements in REQUIRED_MARKERS.items():
        text = texts.get(name, "")
        for rule, alternatives in requirements.items():
            passed = any(marker in text for marker in alternatives)
            checks.append({"check": rule, "source": name, "passed": passed})
            if not passed:
                errors.append({
                    "source": name,
                    "rule": rule,
                    "detail": "missing one of: " + " | ".join(alternatives),
                })

    for name in SCRIPT_SOURCES:
        text = texts.get(name, "")
        match = NETWORK_APIS.search(text)
        passed = match is None
        checks.append({"check": "no_network_transfer_api", "source": name, "passed": passed})
        if match:
            errors.append({"source": name, "rule": "no_network_transfer_api", "detail": match.group(0)})

    report = {
        "version": 63,
        "scope": "interactive tool trust and safety source gate",
        "clinical_review_claimed": False,
        "sources": sorted(texts),
        "content_source": "daily_tools_publisher",
        "seo_wrapper_source": "daily_tools_wrapper",
        "checks": checks,
        "passed_checks": sum(1 for item in checks if item["passed"]),
        "failed_checks": sum(1 for item in checks if not item["passed"]),
        "errors": errors,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
