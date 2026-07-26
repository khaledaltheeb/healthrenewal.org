#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

VERSION = 255
STYLE_ID = "quiz-text-color-v255-style"
RUNTIME_ID = "quiz-text-color-v255-runtime"
REPORT_NAME = "quiz-text-color-v255.json"
HTML_MARKER = 'data-quiz-text-color="v255"'
TEXT_COLOR = "#071a1f"
HEADING_COLOR = "#101828"

STYLE = r'''<style id="quiz-text-color-v255-style">
html[data-quiz-text-color="v255"] body main,
html[data-quiz-text-color="v255"] body main :where(
  h1,h2,h3,h4,h5,h6,p,span,strong,b,em,i,small,label,legend,output,li,dt,dd,
  button,.button,[role="button"],[role="radio"],[data-option],
  .option,.choice,.answer,[class*="option" i],[class*="choice" i],[class*="answer" i]
) {
  color: #071a1f !important;
  -webkit-text-fill-color: #071a1f !important;
  text-shadow: none !important;
  opacity: 1 !important;
}
html[data-quiz-text-color="v255"] body main :where(h1,h2,h3,h4,h5,h6) {
  color: #101828 !important;
  -webkit-text-fill-color: #101828 !important;
}
html[data-quiz-text-color="v255"] body main :where(button,.button,[role="button"],[role="radio"],[data-option]) :where(*) {
  color: #071a1f !important;
  -webkit-text-fill-color: #071a1f !important;
}
@media (prefers-contrast: more) {
  html[data-quiz-text-color="v255"] body main,
  html[data-quiz-text-color="v255"] body main * {
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    text-shadow: none !important;
  }
}
</style>'''

RUNTIME = r'''<script id="quiz-text-color-v255-runtime">
(() => {
  "use strict";
  const VERSION = "v255";
  const TEXT = "#071a1f";
  const HEADING = "#101828";
  const SELECTOR = "h1,h2,h3,h4,h5,h6,p,span,strong,b,em,i,small,label,legend,output,li,dt,dd,button,.button,[role='button'],[role='radio'],[data-option],.option,.choice,.answer,[class*='option' i],[class*='choice' i],[class*='answer' i]";
  const important = (element, property, value) => element.style.setProperty(property, value, "important");
  let observer = null;
  let pending = false;
  const paint = () => {
    pending = false;
    const main = document.querySelector("main");
    if (!main) return;
    if (observer) observer.disconnect();
    const nodes = [main, ...main.querySelectorAll(SELECTOR)];
    nodes.forEach(node => {
      const color = /^H[1-6]$/.test(node.tagName) ? HEADING : TEXT;
      important(node, "color", color);
      important(node, "-webkit-text-fill-color", color);
      important(node, "text-shadow", "none");
      important(node, "opacity", "1");
      node.setAttribute("data-quiz-text-painted", VERSION);
    });
    document.documentElement.setAttribute("data-quiz-text-color", VERSION);
    document.documentElement.setAttribute("data-quiz-text-color-applied", String(nodes.length));
    if (observer) observer.observe(main, {subtree:true,childList:true,attributes:true,attributeFilter:["class","style","aria-checked","hidden"]});
  };
  const schedule = () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(paint);
  };
  const start = () => {
    if (!document.querySelector("main")) return;
    observer = new MutationObserver(schedule);
    paint();
    [50,200,500,1000,2000].forEach(delay => setTimeout(schedule, delay));
  };
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", start, {once:true}) : start();
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
    marker = re.search(r"\bdata-quiz-text-color\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
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
    required = (HTML_MARKER, f'id="{STYLE_ID}"', f'id="{RUNTIME_ID}"', TEXT_COLOR, HEADING_COLOR, "MutationObserver")
    missing = [token for token in required if token not in text]
    if missing:
        raise SystemExit(f"quiz text color contract incomplete: {missing}")
    if text.count(f'id="{STYLE_ID}"') != 1 or text.count(f'id="{RUNTIME_ID}"') != 1:
        raise SystemExit("quiz text color blocks are duplicated")
    report = {
        "version": VERSION,
        "status": "patched",
        "route": "tools/quiz/index.html",
        "changed": changed,
        "quiz_sha256": hashlib.sha256(quiz.read_bytes()).hexdigest(),
        "text_color": TEXT_COLOR,
        "heading_color": HEADING_COLOR,
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
    print(json.dumps(patch(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
