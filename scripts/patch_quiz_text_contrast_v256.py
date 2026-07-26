#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

VERSION = 256
STYLE_ID = "quiz-text-contrast-v256-style"
RUNTIME_ID = "quiz-text-contrast-v256-runtime"
REPORT_NAME = "quiz-text-contrast-v256.json"
HTML_MARKER = 'data-quiz-text-contrast="v256"'

STYLE = r'''<style id="quiz-text-contrast-v256-style">
html[data-quiz-text-contrast="v256"] body main [data-quiz-dark-surface="v256"] {
  color: #eaf7ff !important;
  -webkit-text-fill-color: #eaf7ff !important;
  text-shadow: none !important;
}
html[data-quiz-text-contrast="v256"] body main [data-quiz-dark-surface="v256"] :where(
  h1,h2,h3,h4,h5,h6,p,span,strong,b,em,i,small,label,legend,output,li,dt,dd,
  button,.button,[role="button"],[role="radio"],[data-option],
  .option,.choice,.answer,[class*="option" i],[class*="choice" i],[class*="answer" i]
) {
  color: #eaf7ff !important;
  -webkit-text-fill-color: #eaf7ff !important;
  text-shadow: none !important;
  opacity: 1 !important;
}
html[data-quiz-text-contrast="v256"] body main [data-quiz-dark-surface="v256"] :where(h1,h2,h3,h4,h5,h6) {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
html[data-quiz-text-contrast="v256"] body main [data-quiz-light-surface="v256"] {
  color: #071a1f !important;
  -webkit-text-fill-color: #071a1f !important;
  text-shadow: none !important;
}
html[data-quiz-text-contrast="v256"] body main :where(button,input,select,textarea,[role="radio"]):focus-visible {
  outline: 3px solid #8fd3ff !important;
  outline-offset: 3px !important;
}
@media (prefers-contrast: more) {
  html[data-quiz-text-contrast="v256"] body main [data-quiz-dark-surface="v256"],
  html[data-quiz-text-contrast="v256"] body main [data-quiz-dark-surface="v256"] * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    text-shadow: none !important;
  }
}
</style>'''

RUNTIME = r'''<script id="quiz-text-contrast-v256-runtime">
(() => {
  "use strict";
  const VERSION = "v256";
  const LIGHT_TEXT = "#eaf7ff";
  const HEADING_LIGHT = "#ffffff";
  const DARK_TEXT = "#071a1f";
  const HEADING_DARK = "#101828";
  const SKIP = new Set(["SCRIPT","STYLE","LINK","META","IMG","VIDEO","CANVAS","SVG","PATH"]);
  const TEXT_SELECTOR = [
    "h1","h2","h3","h4","h5","h6","p","span","strong","b","em","i","small",
    "label","legend","output","li","dt","dd","button",".button","[role='button']",
    "[role='radio']","[data-option]",".option",".choice",".answer",
    "[class*='option' i]","[class*='choice' i]","[class*='answer' i]"
  ].join(",");

  const parse = value => {
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
  const important = (element, property, value) => element.style.setProperty(property, value, "important");
  const visible = element => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) >= .05;
  };
  const background = element => {
    const main = document.querySelector("main");
    let node = element;
    while (node && node instanceof HTMLElement) {
      const color = parse(getComputedStyle(node).backgroundColor);
      if (color && color[3] >= .55) return { node, color, dark: luminance(color) < .48 };
      if (node === main) break;
      node = node.parentElement;
    }
    const fallback = parse(getComputedStyle(document.body).backgroundColor) || [255,255,255,1];
    return { node: document.body, color: fallback, dark: luminance(fallback) < .48 };
  };
  const heading = element => /^H[1-6]$/.test(element.tagName);
  const paintNode = element => {
    if (!(element instanceof HTMLElement) || SKIP.has(element.tagName) || !visible(element)) return false;
    const surface = background(element);
    const color = surface.dark ? (heading(element) ? HEADING_LIGHT : LIGHT_TEXT) : (heading(element) ? HEADING_DARK : DARK_TEXT);
    important(element, "color", color);
    important(element, "-webkit-text-fill-color", color);
    important(element, "text-shadow", "none");
    important(element, "opacity", "1");
    element.setAttribute("data-quiz-text-painted", VERSION);
    if (surface.node instanceof HTMLElement && surface.node !== document.body) {
      surface.node.setAttribute(surface.dark ? "data-quiz-dark-surface" : "data-quiz-light-surface", VERSION);
    }
    return true;
  };

  let observer = null;
  let pending = false;
  const apply = () => {
    pending = false;
    const main = document.querySelector("main");
    if (!main) return;
    if (observer) observer.disconnect();
    main.querySelectorAll('[data-quiz-dark-surface="v256"],[data-quiz-light-surface="v256"],[data-quiz-text-painted="v256"]').forEach(node => {
      node.removeAttribute("data-quiz-dark-surface");
      node.removeAttribute("data-quiz-light-surface");
      node.removeAttribute("data-quiz-text-painted");
    });
    let painted = 0;
    main.querySelectorAll(TEXT_SELECTOR).forEach(node => { if (paintNode(node)) painted += 1; });
    document.documentElement.setAttribute("data-quiz-text-contrast", VERSION);
    document.documentElement.setAttribute("data-quiz-text-contrast-applied", String(painted));
    if (observer) observer.observe(main, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["class","style","aria-checked","data-state","hidden"]
    });
  };
  const schedule = () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(apply);
  };
  const start = () => {
    if (!document.querySelector("main")) return;
    observer = new MutationObserver(schedule);
    apply();
    [50,200,500,1000,2000].forEach(delay => setTimeout(schedule, delay));
  };
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", start, { once: true }) : start();
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
    marker = re.search(r"\bdata-quiz-text-contrast\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
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
        "data-quiz-dark-surface",
        "data-quiz-text-painted",
        "MutationObserver",
        'style.setProperty(property, value, "important")',
        LIGHT_TEXT,
        HEADING_LIGHT,
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise SystemExit(f"quiz text contrast contract incomplete: {missing}")
    if text.count(f'id="{STYLE_ID}"') != 1 or text.count(f'id="{RUNTIME_ID}"') != 1:
        raise SystemExit("quiz text contrast blocks are duplicated")

    report = {
        "version": VERSION,
        "status": "patched",
        "route": "tools/quiz/index.html",
        "changed": changed,
        "quiz_sha256": hashlib.sha256(quiz.read_bytes()).hexdigest(),
        "dark_surface_text": LIGHT_TEXT,
        "dark_surface_heading": HEADING_LIGHT,
        "light_surface_text": DARK_TEXT,
        "dynamic_surface_detection": True,
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
