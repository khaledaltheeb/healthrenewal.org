#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

VERSION = 252
REPORT_NAME = "tools-descendant-marshmallow-v250.json"
DESCENDANT_CLASS = "tools-descendant-marshmallow-v250"
DESCENDANT_STYLE_ID = "tools-descendant-marshmallow-v250-style"
QUIZ_ROUTE = "tools/quiz/index.html"
MINIMUM_CONTRAST_RATIO = 4.5

TEXT_COLORS = {
    "ink": "#173f45",
    "muted": "#4d686b",
    "brand": "#075f5b",
    "berry": "#5b2946",
    "button": "#103f42",
}
BACKGROUND_COLORS = {
    "white": "#ffffff",
    "mint": "#e5faf5",
    "rose": "#fff0f5",
    "lilac": "#f2edff",
    "peach": "#fff0e8",
}

DESCENDANT_STYLE = f"""
<style id="{DESCENDANT_STYLE_ID}">
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS}{{
  color-scheme:light!important;
  --tdm-ink:#173f45;--tdm-muted:#4d686b;--tdm-brand:#075f5b;--tdm-berry:#5b2946;
  --tdm-mint:#e5faf5;--tdm-rose:#fff0f5;--tdm-lilac:#f2edff;--tdm-peach:#fff0e8;
  --tdm-line:#b8ddd7;--tdm-focus:#0a7f78;--tdm-danger:#8d243d;--tdm-success:#155f4b;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .quiz,.quiz-shell,.quiz-container,.quiz-content,.quiz-panel,
  .question,.question-container,.question-panel,.question-box,
  .options,.answer,.answer-card,.result,.result-box,.score,.score-box,
  .progress-wrap,.feedback,[data-quiz],[data-question],[data-result],
  [role="radiogroup"],[class*="quiz-"],[class*="question-"],
  [class*="answer-"],[class*="result-"]
){{
  background:linear-gradient(145deg,#fff,var(--tdm-mint))!important;
  color:var(--tdm-ink)!important;
  border-color:var(--tdm-line)!important;
  text-shadow:none!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .option,.option-card,.choice,.choice-card,[data-option],[role="radio"],
  label:has(input[type="radio"]),label:has(input[type="checkbox"])
){{
  background:linear-gradient(145deg,#fff,var(--tdm-rose))!important;
  color:var(--tdm-ink)!important;
  border:1px solid #efc4d3!important;
  border-radius:14px!important;
  text-shadow:none!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .option,.option-card,.choice,.choice-card,[data-option],[role="radio"],
  label:has(input[type="radio"]),label:has(input[type="checkbox"])
) :where(span,small,strong,b,em,i,p,output){{
  color:inherit!important;
  text-shadow:none!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .option,.option-card,.choice,.choice-card,[data-option],[role="radio"],
  label:has(input[type="radio"]),label:has(input[type="checkbox"])
):where(:hover,:focus-within){{
  background:linear-gradient(145deg,#fff,var(--tdm-lilac))!important;
  border-color:#8369a8!important;
  box-shadow:0 0 0 3px rgba(10,127,120,.14)!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .option.selected,.option.is-selected,.choice.selected,.choice.is-selected,
  [data-option][aria-checked="true"],[role="radio"][aria-checked="true"],
  label:has(input[type="radio"]:checked),label:has(input[type="checkbox"]:checked)
){{
  background:linear-gradient(145deg,#fff,var(--tdm-lilac))!important;
  color:var(--tdm-ink)!important;
  border:2px solid #715293!important;
  box-shadow:0 0 0 3px rgba(113,82,147,.14)!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .correct,.is-correct,[data-state="correct"],.feedback[aria-invalid="false"]
){{
  background:linear-gradient(145deg,#fff,var(--tdm-mint))!important;
  color:var(--tdm-success)!important;
  border-color:#68aa96!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .incorrect,.is-incorrect,[data-state="incorrect"],.feedback[aria-invalid="true"]
){{
  background:linear-gradient(145deg,#fff,var(--tdm-rose))!important;
  color:var(--tdm-danger)!important;
  border-color:#c88294!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  h1,h2,h3,h4,h5,h6,.question-title,.result-title,.score-title
){{color:var(--tdm-berry)!important;text-shadow:none!important}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  p,li,dd,small,.hint,.help,.description,.explanation,.feedback,.question-text,
  .answer-text,.result-text,.score-text,[class*="description"],[class*="summary"]
){{color:var(--tdm-muted)!important;text-shadow:none!important}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  label,legend,strong,b,dt,output,.option-text,.choice-text,.answer-label
){{color:var(--tdm-ink)!important;text-shadow:none!important}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(a){{
  color:var(--tdm-brand)!important;
  text-decoration-thickness:.1em;
  text-underline-offset:.22em;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(input,select,textarea){{
  background:#fff!important;color:var(--tdm-ink)!important;border-color:#78aca5!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(input,textarea)::placeholder{{
  color:#536e70!important;opacity:1!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(input[type="radio"],input[type="checkbox"]){{
  accent-color:var(--tdm-focus)!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  button,.button,[role="button"],input[type="submit"],input[type="button"],input[type="reset"]
){{
  background:linear-gradient(145deg,#fff,var(--tdm-mint))!important;
  color:#103f42!important;border:2px solid #61b3a8!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  button,.button,[role="button"],input[type="submit"],input[type="button"],input[type="reset"]
):where(:hover,:focus-visible){{
  background:linear-gradient(145deg,#fff,var(--tdm-lilac))!important;
  border-color:#715293!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  button,.button,[role="button"],input[type="submit"],input[type="button"],input[type="reset"],
  input,select,textarea,label,[role="radio"]
):focus-visible{{
  outline:3px solid var(--tdm-focus)!important;outline-offset:3px!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  button:disabled,input:disabled,select:disabled,textarea:disabled,[aria-disabled="true"]
){{
  background:#edf3f2!important;color:#526769!important;border-color:#aebfbd!important;
  opacity:1!important;cursor:not-allowed!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(progress){{
  color:var(--tdm-focus)!important;background:var(--tdm-lilac)!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(hr){{border-color:var(--tdm-line)!important}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(svg text){{fill:var(--tdm-ink)!important}}
@media(prefers-color-scheme:dark){{
  body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS}{{
    color-scheme:light!important;color:var(--tdm-ink)!important;
  }}
  body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
    .quiz,.quiz-shell,.quiz-container,.quiz-content,.quiz-panel,
    .question,.question-container,.question-panel,.question-box,
    .options,.option,.option-card,.choice,.choice-card,.answer,.answer-card,
    .result,.result-box,.score,.score-box,.progress-wrap,.feedback,
    [data-quiz],[data-question],[data-option],[data-result],
    [role="radiogroup"],[role="radio"]
  ){{
    color-scheme:light!important;color:var(--tdm-ink)!important;
  }}
}}
@media(prefers-contrast:more){{
  body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
    section,article,aside,form,fieldset,.quiz,.question,.option,.choice,.answer,.result,
    [data-question],[data-option],[data-result],[role="radio"]
  ){{background:#fff!important;color:#000!important;border-color:#000!important;box-shadow:none!important}}
}}
@media(prefers-reduced-motion:reduce){{
  body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} *{{
    animation-duration:.01ms!important;animation-iteration-count:1!important;
    transition-duration:.01ms!important;scroll-behavior:auto!important;
  }}
}}
</style>
""".strip()


def _relative_luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    if len(value) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError(f"Invalid hex color: {hex_color}")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_contract() -> dict[str, object]:
    pairs = {
        f"{text_name}_on_{background_name}": round(contrast_ratio(text, background), 3)
        for text_name, text in TEXT_COLORS.items()
        for background_name, background in BACKGROUND_COLORS.items()
    }
    minimum = min(pairs.values())
    return {
        "minimum_ratio": minimum,
        "required_ratio": MINIMUM_CONTRAST_RATIO,
        "passes_wcag_aa_normal_text": minimum >= MINIMUM_CONTRAST_RATIO,
        "pairs": pairs,
    }


def load_identity_module() -> object:
    path = Path(__file__).with_name("enforce_platform_identity_v201.py")
    spec = importlib.util.spec_from_file_location("platform_identity_v201_tools_v252", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load platform identity module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _style_pattern(style_id: str) -> re.Pattern[str]:
    return re.compile(
        rf'<style\b[^>]*\bid\s*=\s*(["\']){re.escape(style_id)}\1[^>]*>.*?</style>',
        re.I | re.S,
    )


def ensure_style_block(text: str, style_id: str, style: str) -> tuple[str, bool, bool]:
    pattern = _style_pattern(style_id)
    matches = list(pattern.finditer(text))
    if len(matches) > 1:
        raise SystemExit(f"Duplicate style block found: {style_id}")
    if matches:
        current = matches[0].group(0)
        if current == style:
            return text, False, False
        updated = text[: matches[0].start()] + style + text[matches[0].end() :]
        return updated, True, True
    if "</head>" not in text.lower():
        raise SystemExit(f"Page head is missing; cannot install style {style_id}")
    updated = re.sub(r"</head>", style + "</head>", text, count=1, flags=re.I)
    return updated, True, False


def ensure_tools_html_marker(text: str, design: str) -> tuple[str, bool]:
    match = re.search(r"<html\b[^>]*>", text, re.I | re.S)
    if not match:
        return text, False
    tag = match.group(0)
    attribute = re.search(
        r'\bdata-tools-design\s*=\s*(["\'])(.*?)\1',
        tag,
        re.I | re.S,
    )
    canonical = f'data-tools-design="{design}"'
    if attribute:
        if attribute.group(2) == design and attribute.group(0) == canonical:
            return text, False
        updated_tag = tag[: attribute.start()] + canonical + tag[attribute.end() :]
    else:
        updated_tag = tag[:-1] + f" {canonical}>"
    return text[: match.start()] + updated_tag + text[match.end() :], True


def ensure_descendant_layer(text: str, identity: object) -> tuple[str, bool, dict[str, bool]]:
    changed = False
    details = {
        "html_marker_added": False,
        "base_class_added": False,
        "descendant_class_added": False,
        "base_style_replaced": False,
        "descendant_style_replaced": False,
    }

    text, updated = ensure_tools_html_marker(text, identity.TOOLS_DESIGN)
    changed = changed or updated
    details["html_marker_added"] = updated

    text, updated = identity._add_class_to_body(text, "tools-marshmallow-v245")
    changed = changed or updated
    details["base_class_added"] = updated

    text, updated = identity._add_class_to_body(text, DESCENDANT_CLASS)
    changed = changed or updated
    details["descendant_class_added"] = updated

    text, updated, replaced = ensure_style_block(
        text,
        identity.TOOLS_STYLE_ID,
        identity.TOOLS_MARSHMALLOW_STYLE,
    )
    changed = changed or updated
    details["base_style_replaced"] = replaced

    text, updated, replaced = ensure_style_block(text, DESCENDANT_STYLE_ID, DESCENDANT_STYLE)
    changed = changed or updated
    details["descendant_style_replaced"] = replaced

    return text, changed, details


def _has_current_style(text: str, style_id: str, style: str) -> bool:
    matches = list(_style_pattern(style_id).finditer(text))
    return len(matches) == 1 and matches[0].group(0) == style


def validate_page(text: str, identity: object, relative: str) -> list[str]:
    missing: list[str] = []
    if not identity._element_has_class(text, "body", "tools-marshmallow-v245"):
        missing.append("body class tools-marshmallow-v245")
    if not identity._element_has_class(text, "body", DESCENDANT_CLASS):
        missing.append(f"body class {DESCENDANT_CLASS}")
    if not _has_current_style(text, identity.TOOLS_STYLE_ID, identity.TOOLS_MARSHMALLOW_STYLE):
        missing.append("current base Marshmallow style")
    if not _has_current_style(text, DESCENDANT_STYLE_ID, DESCENDANT_STYLE):
        missing.append("current descendant Marshmallow style")
    if not re.search(
        rf'\bdata-tools-design\s*=\s*(["\']){re.escape(identity.TOOLS_DESIGN)}\1',
        text,
        re.I | re.S,
    ):
        missing.append(f"data-tools-design={identity.TOOLS_DESIGN}")
    required = (
        "--tm-mint:#e5faf5",
        "--tm-rose:#fff0f5",
        "--tm-lilac:#f2edff",
        "color:var(--tm-ink)!important",
        "background:linear-gradient(145deg,#fff,var(--tdm-mint))!important",
        "color:var(--tdm-ink)!important",
        'label:has(input[type="radio"]:checked)',
        '[role="radio"][aria-checked="true"]',
        "color:inherit!important",
        "::placeholder",
        "@media(prefers-color-scheme:dark)",
        "@media(prefers-contrast:more)",
        "@media(prefers-reduced-motion:reduce)",
    )
    missing.extend(marker for marker in required if marker not in text)
    if missing:
        return [f"{relative}: {marker}" for marker in missing]
    return []


def publish(site: Path) -> dict[str, object]:
    tools_root = site / "tools"
    if not tools_root.is_dir():
        return {
            "version": VERSION,
            "status": "not-applicable",
            "reason": "tools root is absent",
            "pages": 0,
            "updated": 0,
            "quiz_route": QUIZ_ROUTE,
            "quiz_fixed": False,
            "unstyled_pages": [],
        }

    contrast = contrast_contract()
    if not contrast["passes_wcag_aa_normal_text"]:
        raise SystemExit(f"Tools descendant contrast contract failed: {contrast}")

    identity = load_identity_module()
    pages = sorted(tools_root.rglob("*.html"))
    if not pages:
        raise SystemExit(f"No HTML pages found below {tools_root}")

    updated_count = 0
    routes: list[str] = []
    unstyled: list[str] = []
    counters = {
        "html_markers_added": 0,
        "base_classes_added": 0,
        "descendant_classes_added": 0,
        "base_styles_replaced": 0,
        "descendant_styles_replaced": 0,
    }
    for page in pages:
        relative = page.relative_to(site).as_posix()
        routes.append(relative)
        source = page.read_text(encoding="utf-8")
        result, changed, details = ensure_descendant_layer(source, identity)
        if changed:
            page.write_text(result, encoding="utf-8")
            updated_count += 1
        counters["html_markers_added"] += int(details["html_marker_added"])
        counters["base_classes_added"] += int(details["base_class_added"])
        counters["descendant_classes_added"] += int(details["descendant_class_added"])
        counters["base_styles_replaced"] += int(details["base_style_replaced"])
        counters["descendant_styles_replaced"] += int(details["descendant_style_replaced"])
        unstyled.extend(validate_page(result, identity, relative))

    quiz_page = site / QUIZ_ROUTE
    quiz_fixed = quiz_page.is_file() and not validate_page(
        quiz_page.read_text(encoding="utf-8"), identity, QUIZ_ROUTE
    )
    if not quiz_page.is_file():
        unstyled.append(f"{QUIZ_ROUTE}: missing page")
    if unstyled:
        raise SystemExit(f"Tools descendant Marshmallow contract failed: {unstyled[:20]}")

    report: dict[str, object] = {
        "version": VERSION,
        "status": "published",
        "scope": "tools/**/*.html",
        "pages": len(pages),
        "child_pages": sum(route != "tools/index.html" for route in routes),
        "updated": updated_count,
        "unchanged": len(pages) - updated_count,
        "quiz_route": QUIZ_ROUTE,
        "quiz_fixed": quiz_fixed,
        "base_design": identity.TOOLS_DESIGN,
        "descendant_class": DESCENDANT_CLASS,
        "descendant_style": DESCENDANT_STYLE_ID,
        "style_replacement_enabled": True,
        "selected_states_styled": True,
        "nested_option_text_forced": True,
        "disabled_states_styled": True,
        "dark_mode_blackening_blocked": True,
        "high_contrast_supported": True,
        "reduced_motion_supported": True,
        "contrast": contrast,
        "mutations": counters,
        "unstyled_pages": [],
        "routes": routes,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_NAME).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    report = publish(site)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
