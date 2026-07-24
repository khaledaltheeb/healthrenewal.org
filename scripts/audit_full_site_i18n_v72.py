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


def main() -> int:
    # Apply the same metadata contract used to seal the production artifact before auditing.
    publish_global_metadata()
    metadata_path = Path(sys.argv[1] if len(sys.argv) > 1 else "_site") / "api" / "global-metadata-v27.json"
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
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
