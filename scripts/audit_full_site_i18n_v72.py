#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "scripts" / "audit_full_site_v16.py"
LOCALE_CONTRACTS = {
    "en": ("en", "ltr"),
    "es": ("es", "ltr"),
}
BOOLEAN_SCRIPT_ATTRIBUTES = ("defer", "async")


def expected_language_direction(relative_path: str) -> tuple[str, str]:
    parts = Path(relative_path).parts
    if parts and parts[0] in LOCALE_CONTRACTS:
        return LOCALE_CONTRACTS[parts[0]]
    return "ar", "rtl"


def normalize_boolean_script_attributes(parser) -> None:
    """Preserve presence semantics for HTML boolean attributes parsed as None."""
    for script in parser.scripts:
        for attribute in BOOLEAN_SCRIPT_ATTRIBUTES:
            if attribute in script and script[attribute] is None:
                script[attribute] = attribute


def legacy_render_blocking_decision(script: dict[str, str | None]) -> bool:
    src = str(script.get("src", ""))
    return bool(
        src
        and not script.get("defer")
        and not script.get("async")
        and str(script.get("type", "")).lower() != "module"
    )


def verify_boolean_attribute_contract(module) -> None:
    parser = module.AuditParser()
    parser.feed(
        '<script src="deferred.js" defer></script>'
        '<script src="async.js" async></script>'
        '<script src="module.js" type="module"></script>'
        '<script src="blocking.js"></script>'
    )
    normalize_boolean_script_attributes(parser)
    observed = [legacy_render_blocking_decision(script) for script in parser.scripts]
    expected = [False, False, False, True]
    if observed != expected:
        raise SystemExit(
            f"Render-blocking boolean attribute contract failed: {observed} != {expected}"
        )


def main() -> int:
    spec = importlib.util.spec_from_file_location("audit_full_site_v16_legacy", LEGACY)
    if spec is None or spec.loader is None:
        raise SystemExit("Could not load legacy full-site auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify_boolean_attribute_contract(module)

    original_parse_page = module.parse_page
    locale_page_counts: Counter[str] = Counter()
    contract_errors: list[str] = []

    def locale_aware_parse_page(path: Path):
        parser = original_parse_page(path)
        normalize_boolean_script_attributes(parser)
        rel = path.relative_to(module.SITE).as_posix()
        expected_lang, expected_dir = expected_language_direction(rel)
        locale_page_counts[expected_lang] += 1
        actual_lang = parser.html_attrs.get("lang")
        actual_dir = parser.html_attrs.get("dir")
        if actual_lang != expected_lang or actual_dir != expected_dir:
            contract_errors.append(
                f"Locale contract mismatch in {rel}: expected {expected_lang}/{expected_dir}, "
                f"found {actual_lang}/{actual_dir}"
            )
        # The v16 auditor predates multilingual output and checks only ar/rtl.
        # Normalize only the parser view after validating the real document above;
        # every other metadata, link, content and accessibility check remains unchanged.
        parser.html_attrs = dict(parser.html_attrs)
        parser.html_attrs["lang"] = "ar"
        parser.html_attrs["dir"] = "rtl"
        return parser

    module.parse_page = locale_aware_parse_page
    result = module.main()

    if contract_errors:
        raise SystemExit("\n".join(contract_errors[:80]))

    report_path = module.SITE / "api" / "full-site-audit-v16.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["version"] = "16-i18n-v72"
    report["locale_contracts"] = {
        "ar": {"lang": "ar", "dir": "rtl"},
        **{
            locale: {"lang": contract[0], "dir": contract[1]}
            for locale, contract in LOCALE_CONTRACTS.items()
        },
    }
    report["locale_page_counts"] = dict(sorted(locale_page_counts.items()))
    report["locale_contract_error_count"] = 0
    report["render_blocking_detection"] = "boolean-attribute-presence-v25"
    report["render_blocking_boolean_attribute_contract"] = True
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "audit": "passed",
                "version": report["version"],
                "locale_page_counts": report["locale_page_counts"],
                "locale_contract_error_count": 0,
                "render_blocking_detection": report["render_blocking_detection"],
                "blocking_scripts": report.get("blocking_scripts", 0),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
