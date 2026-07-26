#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

from publish_global_metadata_v27 import main as publish_global_metadata


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "scripts" / "audit_full_site_v16.py"
LOCALE_CONTRACTS = {
    "en": ("en", "ltr"),
    "es": ("es", "ltr"),
}
BOOLEAN_SCRIPT_ATTRIBUTES = ("defer", "async")
PRACTICAL_TIPS_EXPECTED_HTML = 111
PRACTICAL_TIPS_LEGACY_HTML = 21


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


def install_accessible_anchor_parser(module):
    """Upgrade legacy empty-link detection to use the accessible-name inputs it omitted."""
    legacy_parser = module.AuditParser

    class AccessibleAuditParser(legacy_parser):
        def __init__(self) -> None:
            super().__init__()
            self._accessible_anchor_stack: list[dict[str, object]] = []

        def handle_starttag(self, tag, attrs) -> None:
            values = dict(attrs)
            if tag == "a":
                self._accessible_anchor_stack.append({"attrs": values, "image_alts": []})
            elif tag == "img" and self._accessible_anchor_stack:
                alt = values.get("alt")
                if alt:
                    self._accessible_anchor_stack[-1]["image_alts"].append(str(alt))
            super().handle_starttag(tag, attrs)

        def handle_endtag(self, tag: str) -> None:
            super().handle_endtag(tag)
            if tag != "a" or not self._accessible_anchor_stack or not self.anchor_texts:
                return
            record = self._accessible_anchor_stack.pop()
            if self.anchor_texts[-1]:
                return
            attrs = record["attrs"]
            image_alts = record["image_alts"]
            accessible_name = (
                attrs.get("aria-label")
                or (f"aria-labelledby:{attrs['aria-labelledby']}" if attrs.get("aria-labelledby") else "")
                or attrs.get("title")
                or " ".join(image_alts)
            )
            if accessible_name:
                self.anchor_texts[-1] = str(accessible_name).strip()

    module.AuditParser = AccessibleAuditParser
    return AccessibleAuditParser


def verify_accessible_link_contract(parser_class) -> None:
    parser = parser_class()
    parser.feed(
        '<a href="/text">رابط نصي</a>'
        '<a href="/aria" aria-label="الرئيسية"></a>'
        '<a href="/labelled" aria-labelledby="label-id"></a>'
        '<a href="/title" title="الدليل"></a>'
        '<a href="/image"><img src="logo.png" alt="شعار المنصة"></a>'
        '<a href="/unnamed"></a>'
    )
    observed = [bool(value.strip()) for value in parser.anchor_texts]
    expected = [True, True, True, True, True, False]
    if observed != expected:
        raise SystemExit(f"Accessible link-name contract failed: {observed} != {expected}")


def load_practical_tips_contract(site: Path) -> dict | None:
    report_path = site / "api" / "practical-tips-v237.json"
    if not report_path.is_file():
        return None
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected = {
        "version": 237,
        "status": "passed",
        "guide_count": 100,
        "preserved_existing_guides": 20,
        "new_guides": 80,
        "pillar_count": 10,
        "minimum_required_words": 700,
        "remaining_below_minimum": 0,
        "missing_or_failed": 0,
        "duplicate_slugs": 0,
        "duplicate_titles": 0,
        "sitemap_urls": 111,
        "core_sections_compatibility": "passed",
        "compatibility_pages": 100,
        "unique_titles": 100,
        "unique_descriptions": 100,
        "topic_depth_status": "passed",
        "topic_depth_pages": 10,
    }
    invalid = {
        key: {"actual": report.get(key), "expected": value}
        for key, value in expected.items()
        if report.get(key) != value
    }
    if int(report.get("category_count", 0)) < 25:
        invalid["category_count"] = {"actual": report.get("category_count"), "expected_minimum": 25}
    if int(report.get("minimum_after_words", 0)) < 700:
        invalid["minimum_after_words"] = {"actual": report.get("minimum_after_words"), "expected_minimum": 700}
    if int(report.get("minimum_topic_characters", 0)) < 1800:
        invalid["minimum_topic_characters"] = {
            "actual": report.get("minimum_topic_characters"),
            "expected_minimum": 1800,
        }
    if invalid:
        raise SystemExit({"invalid_practical_tips_v237_contract": invalid})
    return report


def run_legacy_with_practical_tips_upgrade(module, tips_contract: dict | None) -> tuple[int, dict]:
    report_path = module.SITE / "api" / "full-site-audit-v16.json"
    caught: SystemExit | None = None
    try:
        result = int(module.main() or 0)
    except SystemExit as exc:
        caught = exc
        result = 1

    if not report_path.is_file():
        if caught is not None:
            raise caught
        raise SystemExit("Legacy full-site audit did not create its report")
    report = json.loads(report_path.read_text(encoding="utf-8"))

    if tips_contract is None:
        if caught is not None:
            raise caught
        return result, report

    obsolete_error = (
        f"Unexpected HTML count for tips: {PRACTICAL_TIPS_EXPECTED_HTML} "
        f"!= {PRACTICAL_TIPS_LEGACY_HTML}"
    )
    errors = list(report.get("errors", []))
    remaining = [error for error in errors if error != obsolete_error]
    actual_tips = int(report.get("section_counts", {}).get("tips", 0))
    if actual_tips != PRACTICAL_TIPS_EXPECTED_HTML:
        remaining.append(
            f"Practical tips v237 HTML count is {actual_tips}, "
            f"expected {PRACTICAL_TIPS_EXPECTED_HTML}"
        )

    if remaining:
        if caught is not None:
            raise caught
        raise SystemExit("\n".join(remaining[:100]))

    if caught is not None and obsolete_error not in errors:
        raise caught

    report["error_count"] = 0
    report["errors"] = []
    report["tips_contract_version"] = 237
    report["expected_tips_html"] = PRACTICAL_TIPS_EXPECTED_HTML
    report["tips_guides"] = int(tips_contract["guide_count"])
    report["tips_topic_pages"] = int(tips_contract["topic_depth_pages"])
    report["tips_sitemap_urls"] = int(tips_contract["sitemap_urls"])
    report["tips_minimum_words"] = int(tips_contract["minimum_after_words"])
    report["tips_minimum_topic_characters"] = int(tips_contract["minimum_topic_characters"])
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0, report


def main() -> int:
    publish_global_metadata()
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    metadata_path = site / "api" / "global-metadata-v27.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") != "passed" or int(metadata.get("remaining_missing_count", -1)) != 0:
        raise SystemExit({"invalid_global_metadata_evidence": metadata})

    spec = importlib.util.spec_from_file_location("audit_full_site_v16_legacy", LEGACY)
    if spec is None or spec.loader is None:
        raise SystemExit("Could not load legacy full-site auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    verify_boolean_attribute_contract(module)
    accessible_parser = install_accessible_anchor_parser(module)
    verify_accessible_link_contract(accessible_parser)

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
        parser.html_attrs = dict(parser.html_attrs)
        parser.html_attrs["lang"] = "ar"
        parser.html_attrs["dir"] = "rtl"
        return parser

    module.parse_page = locale_aware_parse_page
    tips_contract = load_practical_tips_contract(module.SITE)
    result, report = run_legacy_with_practical_tips_upgrade(module, tips_contract)

    if contract_errors:
        raise SystemExit("\n".join(contract_errors[:80]))

    report_path = module.SITE / "api" / "full-site-audit-v16.json"
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
    report["accessible_link_detection"] = "text-or-aria-label-labelledby-title-image-alt-v26"
    report["accessible_link_name_contract"] = True
    report["global_metadata_version"] = int(metadata["version"])
    report["global_metadata_pages"] = int(metadata["pages_scanned"])
    report["global_metadata_remaining_missing"] = int(metadata["remaining_missing_count"])
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
                "accessible_link_detection": report["accessible_link_detection"],
                "empty_links": report.get("empty_links", 0),
                "global_metadata_version": report["global_metadata_version"],
                "global_metadata_remaining_missing": 0,
                "tips_contract_version": report.get("tips_contract_version", 15),
                "tips_html": report.get("section_counts", {}).get("tips", 0),
                "tips_expected_html": report.get("expected_tips_html", PRACTICAL_TIPS_LEGACY_HTML),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
