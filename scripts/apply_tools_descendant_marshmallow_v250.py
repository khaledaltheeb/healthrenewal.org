#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

VERSION = 250
REPORT_NAME = "tools-descendant-marshmallow-v250.json"
DESCENDANT_CLASS = "tools-descendant-marshmallow-v250"
DESCENDANT_STYLE_ID = "tools-descendant-marshmallow-v250-style"
QUIZ_ROUTE = "tools/quiz/index.html"

DESCENDANT_STYLE = f"""
<style id="{DESCENDANT_STYLE_ID}">
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS}{{
  color-scheme:light!important;
  --tdm-ink:#173f45;--tdm-muted:#4d686b;--tdm-brand:#075f5b;--tdm-berry:#5b2946;
  --tdm-mint:#e5faf5;--tdm-rose:#fff0f5;--tdm-lilac:#f2edff;--tdm-peach:#fff0e8;
  --tdm-line:#b8ddd7;--tdm-focus:#0a7f78;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .quiz,.quiz-shell,.quiz-container,.quiz-content,.quiz-panel,
  .question,.question-container,.question-panel,.question-box,
  .options,.option,.option-card,.choice,.choice-card,.answer,.answer-card,
  .result,.result-box,.score,.score-box,.progress-wrap,.feedback,
  [class*="quiz-"],[class*="question-"],[class*="option-"],
  [class*="choice-"],[class*="answer-"],[class*="result-"]
){{
  background:linear-gradient(145deg,#fff,var(--tdm-mint))!important;
  color:var(--tdm-ink)!important;
  border-color:var(--tdm-line)!important;
  text-shadow:none!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .option,.option-card,.choice,.choice-card,label[for]
){{
  background:linear-gradient(145deg,#fff,var(--tdm-rose))!important;
  color:var(--tdm-ink)!important;
  border:1px solid #efc4d3!important;
  border-radius:14px!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
  .option,.option-card,.choice,.choice-card,label[for]
):where(:hover,:focus-within){{
  background:linear-gradient(145deg,#fff,var(--tdm-lilac))!important;
  border-color:#9a7fc0!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  h1,h2,h3,h4,h5,h6,.question-title,.result-title,.score-title
){{color:var(--tdm-berry)!important;text-shadow:none!important}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  p,li,small,.hint,.help,.description,.explanation,.feedback,.question-text,
  .answer-text,.result-text,.score-text
){{color:var(--tdm-muted)!important;text-shadow:none!important}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(
  label,legend,strong,b,span,output
){{text-shadow:none!important}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(input,select,textarea){{
  background:#fff!important;color:var(--tdm-ink)!important;border-color:#86bdb5!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(input[type="radio"],input[type="checkbox"]){{
  accent-color:var(--tdm-focus)!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(button,.button,[role="button"],input[type="submit"]){{
  background:linear-gradient(145deg,#fff,var(--tdm-mint))!important;
  color:#103f42!important;border:2px solid #72c5ba!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(button,.button,[role="button"],input[type="submit"]):focus-visible,
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(a,input,select,textarea,label):focus-visible{{
  outline:3px solid var(--tdm-focus)!important;outline-offset:3px!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(progress){{
  color:var(--tdm-focus)!important;background:var(--tdm-lilac)!important;
}}
body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} :where(hr){{border-color:var(--tdm-line)!important}}
@media(prefers-color-scheme:dark){{
  body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS},
  body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
    .quiz,.quiz-shell,.quiz-container,.quiz-content,.quiz-panel,
    .question,.question-container,.question-panel,.question-box,
    .options,.option,.option-card,.choice,.choice-card,.answer,.answer-card,
    .result,.result-box,.score,.score-box,.progress-wrap,.feedback
  ){{color-scheme:light!important;color:var(--tdm-ink)!important}}
}}
@media(prefers-contrast:more){{
  body.{DESCENDANT_CLASS}.{DESCENDANT_CLASS} main :where(
    section,article,aside,form,fieldset,.quiz,.question,.option,.choice,.answer,.result
  ){{background:#fff!important;color:#000!important;border-color:#000!important;box-shadow:none!important}}
}}
</style>
""".strip()


def load_identity_module() -> object:
    path = Path(__file__).with_name("enforce_platform_identity_v201.py")
    spec = importlib.util.spec_from_file_location("platform_identity_v201_tools_v250", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load platform identity module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_descendant_layer(text: str, identity: object) -> tuple[str, bool]:
    changed = False
    text, updated = identity.ensure_tools_marshmallow(text)
    changed = changed or updated
    text, updated = identity._add_class_to_body(text, DESCENDANT_CLASS)
    changed = changed or updated
    if DESCENDANT_STYLE_ID not in text:
        if "</head>" not in text.lower():
            raise SystemExit("Tools descendant page head is missing")
        text = re.sub(r"</head>", DESCENDANT_STYLE + "</head>", text, count=1, flags=re.I)
        changed = True
    return text, changed


def validate_page(text: str, identity: object, relative: str) -> list[str]:
    missing: list[str] = []
    if not identity._element_has_class(text, "body", "tools-marshmallow-v245"):
        missing.append("body class tools-marshmallow-v245")
    if not identity._element_has_class(text, "body", DESCENDANT_CLASS):
        missing.append(f"body class {DESCENDANT_CLASS}")
    if text.count(identity.TOOLS_STYLE_ID) != 1:
        missing.append("one base Marshmallow style")
    if text.count(DESCENDANT_STYLE_ID) != 1:
        missing.append("one descendant Marshmallow style")
    required = (
        f'data-tools-design="{identity.TOOLS_DESIGN}"',
        "--tm-mint:#e5faf5",
        "--tm-rose:#fff0f5",
        "--tm-lilac:#f2edff",
        "color:var(--tm-ink)!important",
        "background:linear-gradient(145deg,#fff,var(--tdm-mint))!important",
        "color:var(--tdm-ink)!important",
        "@media(prefers-color-scheme:dark)",
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

    identity = load_identity_module()
    pages = sorted(tools_root.rglob("*.html"))
    if not pages:
        raise SystemExit(f"No HTML pages found below {tools_root}")

    updated_count = 0
    routes: list[str] = []
    unstyled: list[str] = []
    for page in pages:
        relative = page.relative_to(site).as_posix()
        routes.append(relative)
        source = page.read_text(encoding="utf-8")
        result, changed = ensure_descendant_layer(source, identity)
        if changed:
            page.write_text(result, encoding="utf-8")
            updated_count += 1
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
        "dark_mode_blackening_blocked": True,
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
