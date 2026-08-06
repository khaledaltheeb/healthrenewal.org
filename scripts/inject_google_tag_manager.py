#!/usr/bin/env python3
"""Inject Google Tag Manager into every HTML document in a static site.

The operation is idempotent: rerunning the script will not duplicate either GTM block.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

GTM_ID = "GTM-WBLQVBG4"
SCRIPT_VERSION = "1.0.0"

HEAD_SNIPPET = """<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-WBLQVBG4');</script>
<!-- End Google Tag Manager -->"""

BODY_SNIPPET = """<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-WBLQVBG4"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->"""

HEAD_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
BODY_RE = re.compile(r"<body\b[^>]*>", re.IGNORECASE)
HEAD_MARKER_RE = re.compile(
    rf"googletagmanager\.com/gtm\.js\?id=.*?{re.escape(GTM_ID)}|"
    rf"\(window,document,'script','dataLayer','{re.escape(GTM_ID)}'\)",
    re.IGNORECASE | re.DOTALL,
)
BODY_MARKER_RE = re.compile(
    rf"googletagmanager\.com/ns\.html\?id={re.escape(GTM_ID)}",
    re.IGNORECASE,
)

SKIP_PARTS = {".git", "node_modules", "vendor", "dist", "build", "coverage"}


def newline_for(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def inject_after_opening_tag(text: str, pattern: re.Pattern[str], snippet: str) -> tuple[str, bool]:
    match = pattern.search(text)
    if not match:
        return text, False
    nl = newline_for(text)
    replacement = f"{match.group(0)}{nl}{snippet.replace(chr(10), nl)}{nl}"
    return text[: match.start()] + replacement + text[match.end() :], True


def patch_html(path: Path) -> tuple[bool, list[str]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = raw.decode("utf-8-sig")
        encoding = "utf-8-sig"

    changed = False
    warnings: list[str] = []

    if not HEAD_MARKER_RE.search(text):
        text, inserted = inject_after_opening_tag(text, HEAD_RE, HEAD_SNIPPET)
        if inserted:
            changed = True
        else:
            warnings.append("missing <head>")

    if not BODY_MARKER_RE.search(text):
        text, inserted = inject_after_opening_tag(text, BODY_RE, BODY_SNIPPET)
        if inserted:
            changed = True
        else:
            warnings.append("missing <body>")

    if changed:
        path.write_text(text, encoding=encoding, newline="")

    return changed, warnings


def iter_html_files(root: Path):
    for path in root.rglob("*.html"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.is_file():
            yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true", help="Exit 1 when files still need modification")
    args = parser.parse_args()

    root = args.root.resolve()
    changed_files: list[Path] = []
    warnings: list[tuple[Path, str]] = []

    for path in iter_html_files(root):
        changed, file_warnings = patch_html(path)
        if changed:
            changed_files.append(path)
        warnings.extend((path, warning) for warning in file_warnings)

    for path in changed_files:
        print(f"UPDATED {path.relative_to(root)}")
    for path, warning in warnings:
        print(f"WARNING {path.relative_to(root)}: {warning}", file=sys.stderr)

    print(
        f"GTM injection complete: {len(changed_files)} updated, "
        f"{len(warnings)} structural warnings."
    )

    if args.check and changed_files:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
