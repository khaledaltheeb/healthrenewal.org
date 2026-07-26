#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

VERSION = 254
STYLE_ID = "quiz-contrast-v254-style"
RUNTIME_ID = "quiz-contrast-v254-runtime"
REPORT_NAME = "quiz-contrast-v254.json"
HTML_MARKER = 'data-quiz-contrast="v254"'

STYLE = r'''<style id="quiz-contrast-v254-style">
html[data-quiz-contrast="v254"],
html[data-quiz-contrast="v254"] body {
  color-scheme: light !important;
}
html[data-quiz-contrast="v254"] body main :where(
  section, article, form, fieldset,
  [data-quiz], [data-question], [data-result], [role="radiogroup"],
  [id*="quiz" i], [class*="quiz" i], [class*="question" i],
  [class*="result" i], [class*="score" i], [class*="card" i],
  [class*="panel" i], [class*="box" i]
) {
  background: linear-gradient(145deg, #ffffff 0%, #eefcf8 100%) !important;
  background-color: #ffffff !important;
  color: #173f45 !important;
  border-color: #b8ddd7 !important;
  text-shadow: none !important;
  color-scheme: light !important;
}
html[data-quiz-contrast="v254"] body main :where(
  button, .button, [role="button"], [role="radio"], [data-option],
  .option, .choice, .answer,
  [class*="option" i], [class*="choice" i], [class*="answer" i],
  label:has(input[type="radio"]), label:has(input[type="checkbox"])
) {
  background: linear-gradient(145deg, #ffffff 0%, #fff3f7 100%) !important;
  background-color: #ffffff !important;
  color: #173f45 !important;
  border: 1px solid #e4afc1 !important;
  border-radius: 14px !important;
  text-shadow: none !important;
  opacity: 1 !important;
}
html[data-quiz-contrast="v254"] body main :where(
  h1, h2, h3, h4, h5, h6, p, span, strong, b, em, small,
  label, legend, output, li, dt, dd
) {
  color: #173f45 !important;
  text-shadow: none !important;
}
html[data-quiz-contrast="v254"] body main :where(h1, h2, h3, h4, h5, h6) {
  color: #5b2946 !important;
}
html[data-quiz-contrast="v254"] body main :where(
  .selected, .is-selected, [aria-checked="true"],
  label:has(input:checked)
) {
  background: linear-gradient(145deg, #ffffff 0%, #f2edff 100%) !important;
  border: 2px solid #715293 !important;
  color: #173f45 !important;
}
html[data-quiz-contrast="v254"] body main :where(input, select, textarea) {
  background: #ffffff !important;
  color: #173f45 !important;
  border-color: #78aca5 !important;
  color-scheme: light !important;
}
html[data-quiz-contrast="v254"] body main :where(button, input, select, textarea, [role="radio"]):focus-visible {
  outline: 3px solid #087f78 !important;
  outline-offset: 3px !important;
}
@media (prefers-color-scheme: dark) {
  html[data-quiz-contrast="v254"],
  html[data-quiz-contrast="v254"] body {
    color-scheme: light !important;
  }
}
@media (prefers-contrast: more) {
  html[data-quiz-contrast="v254"] body main :where(section, article, form, fieldset, button, [role="radio"]) {
    background: #ffffff !important;
    color: #000000 !important;
    border-color: #000000 !important;
    box-shadow: none !important;
  }
}
@media (prefers-reduced-motion: reduce) {
  html[data-quiz-contrast="v254"] body * {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>'''

RUNTIME = r'''<script id="quiz-contrast-v254-runtime">
(() => {
  "use strict";
  const VERSION = "v254";
  const SKIP = new Set(["SCRIPT", "STYLE", "LINK", "META", "IMG", "VIDEO", "CANVAS", "SVG", "PATH"]);
  const TEXT_SELECTOR = "h1,h2,h3,h4,h5,h6,p,span,strong,b,em,i,small,label,legend,output,li,dt,dd";
  const OPTION_SELECTOR = [
    "button", ".button", "[role='button']", "[role='radio']", "[data-option]",
    ".option", ".choice", ".answer", "[class*='option' i]",
    "[class*='choice' i]", "[class*='answer' i]",
    "label:has(input[type='radio'])", "label:has(input[type='checkbox'])"
  ].join(",");

  const parseColor = value => {
    const match = String(value || "").match(/rgba?\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)(?:\s*,\s*(\d*(?:\.\d+)?))?\s*\)/i);
    return match ? [+match[1], +match[2], +match[3], match[4] === undefined || match[4] === "" ? 1 : +match[4]] : null;
  };
  const luminance = color => {
    const channels = color.slice(0, 3).map(value => {
      value /= 255;
      return value <= .04045 ? value / 12.92 : Math.pow((value + .055) / 1.055, 2.4);
    });
    return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
  };
  const visibleDarkSurface = element => {
    if (!(element instanceof HTMLElement) || SKIP.has(element.tagName)) return false;
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    const color = parseColor(style.backgroundColor);
    return rect.width >= 160 && rect.height >= 42 && style.display !== "none" &&
      style.visibility !== "hidden" && Number(style.opacity) >= .05 &&
      color && color[3] > .45 && luminance(color) < .48;
  };
  const important = (element, property, value) => element.style.setProperty(property, value, "important");
  const isSelected = element => element.matches(".selected,.is-selected,[aria-checked='true']") || Boolean(element.querySelector("input:checked"));

  const paintText = (root, color = "#173f45") => {
    root.querySelectorAll(TEXT_SELECTOR).forEach(node => {
      important(node, "color", /^H[1-6]$/.test(node.tagName) ? "#5b2946" : color);
      important(node, "text-shadow", "none");
    });
  };
  const paintSurface = element => {
    if (!(element instanceof HTMLElement) || SKIP.has(element.tagName)) return;
    const option = element.matches(OPTION_SELECTOR);
    const selected = option && isSelected(element);
    important(element, "background", selected
      ? "linear-gradient(145deg,#ffffff 0%,#f2edff 100%)"
      : option
        ? "linear-gradient(145deg,#ffffff 0%,#fff3f7 100%)"
        : "linear-gradient(145deg,#ffffff 0%,#eefcf8 100%)");
    important(element, "background-color", "#ffffff");
    important(element, "color", "#173f45");
    important(element, "border-color", selected ? "#715293" : option ? "#e4afc1" : "#b8ddd7");
    important(element, "text-shadow", "none");
    important(element, "color-scheme", "light");
    if (option) {
      important(element, "border-style", "solid");
      important(element, "border-width", selected ? "2px" : "1px");
      important(element, "border-radius", "14px");
      important(element, "opacity", "1");
    }
    paintText(element);
    element.setAttribute("data-quiz-contrast-painted", VERSION);
  };

  let observer = null;
  let scheduled = false;
  const apply = () => {
    scheduled = false;
    const main = document.querySelector("main");
    if (!main) return;
    if (observer) observer.disconnect();
    const targets = new Set(main.querySelectorAll(OPTION_SELECTOR));
    main.querySelectorAll("section,article,form,fieldset,[data-quiz],[data-question],[data-result],[role='radiogroup'],[id*='quiz' i],[class*='quiz' i],[class*='question' i],[class*='result' i],[class*='score' i],[class*='card' i],[class*='panel' i],[class*='box' i]").forEach(node => targets.add(node));
    main.querySelectorAll("*").forEach(node => {
      if (visibleDarkSurface(node)) targets.add(node);
    });
    targets.forEach(paintSurface);
    paintText(main);
    document.documentElement.setAttribute("data-quiz-contrast", VERSION);
    document.documentElement.setAttribute("data-quiz-contrast-applied", String(targets.size));
    if (observer) observer.observe(main, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["class", "style", "aria-checked", "data-state", "hidden"]
    });
  };
  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(apply);
  };
  const start = () => {
    if (!document.querySelector("main")) return;
    observer = new MutationObserver(schedule);
    apply();
    [50, 200, 500, 1000, 2000].forEach(delay => setTimeout(schedule, delay));
  };
  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", start, { once: true })
    : start();
})();
</script>'''


def block_pattern(tag: str, block_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"<{tag}\b[^>]*\bid\s*=\s*([\"']){re.escape(block_id)}\1[^>]*>.*?</{tag}>",
        re.I | re.S,
    )


def replace_or_insert(text: str, tag: str, block_id: str, block: str, closing_tag: str) -> tuple[str, bool]:
    pattern = block_pattern(tag, block_id)
    matches = list(pattern.finditer(text))
    if len(matches) > 1:
        raise SystemExit(f"duplicate block {block_id}")
    if matches:
        old = matches[0].group(0)
        if old == block:
            return text, False
        return text[: matches[0].start()] + block + text[matches[0].end() :], True
    if closing_tag.lower() not in text.lower():
        raise SystemExit(f"missing {closing_tag}")
    return re.sub(re.escape(closing_tag), lambda match: block + match.group(0), text, count=1, flags=re.I), True


def mark_html(text: str) -> tuple[str, bool]:
    match = re.search(r"<html\b[^>]*>", text, re.I | re.S)
    if not match:
        raise SystemExit("missing html element")
    tag = match.group(0)
    marker = re.search(r"\bdata-quiz-contrast\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
    if marker and marker.group(0) == HTML_MARKER:
        return text, False
    if marker:
        updated = tag[: marker.start()] + HTML_MARKER + tag[marker.end() :]
    else:
        updated = tag[:-1] + " " + HTML_MARKER + ">"
    return text[: match.start()] + updated + text[match.end() :], True


def patch(site: Path) -> dict[str, object]:
    quiz = site / "tools" / "quiz" / "index.html"
    if not quiz.is_file():
        raise SystemExit(f"missing quiz page: {quiz}")

    source = quiz.read_text(encoding="utf-8")
    text, marker_changed = mark_html(source)
    text, style_changed = replace_or_insert(text, "style", STYLE_ID, STYLE, "</head>")
    text, runtime_changed = replace_or_insert(text, "script", RUNTIME_ID, RUNTIME, "</body>")
    changed = marker_changed or style_changed or runtime_changed
    if changed:
        quiz.write_text(text, encoding="utf-8")

    required = (
        HTML_MARKER,
        f'id="{STYLE_ID}"',
        f'id="{RUNTIME_ID}"',
        "data-quiz-contrast-painted",
        "MutationObserver",
        'style.setProperty(property, value, "important")',
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise SystemExit(f"quiz contrast contract incomplete: {missing}")
    if text.count(f'id="{STYLE_ID}"') != 1 or text.count(f'id="{RUNTIME_ID}"') != 1:
        raise SystemExit("quiz contrast blocks are duplicated")

    report = {
        "version": VERSION,
        "status": "patched",
        "route": "tools/quiz/index.html",
        "changed": changed,
        "quiz_sha256": hashlib.sha256(quiz.read_bytes()).hexdigest(),
        "light_surface": True,
        "dark_text": True,
        "dynamic_dom_repair": True,
        "inline_important_override": True,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    report = patch(args.site.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
