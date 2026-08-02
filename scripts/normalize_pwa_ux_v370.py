#!/usr/bin/env python3
"""Normalize installability and responsive UX metadata across production HTML."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION = 370
ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".github",
    "_site",
    "node_modules",
    "vendor",
    "fixtures",
    "snapshots",
    "coverage",
    "reports",
}
NO_UX_SCRIPT_PATHS = {
    "provider-assessment-demo/professional-console.html",
}
VERIFY_RE = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.IGNORECASE,
)
HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)
BODY_OPEN_RE = re.compile(r"<body\b(?P<attrs>[^>]*)>", re.IGNORECASE | re.DOTALL)
BLOCK_START = "<!-- pt-pwa-ux:v370:start -->"
BLOCK_END = "<!-- pt-pwa-ux:v370:end -->"
BLOCK_RE = re.compile(
    r"\s*<!-- pt-pwa-ux:v370:start -->.*?<!-- pt-pwa-ux:v370:end -->\s*",
    re.IGNORECASE | re.DOTALL,
)

PATTERNS = {
    "viewport": re.compile(
        r'<meta\b[^>]*\bname\s*=\s*(["\'])viewport\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "theme": re.compile(
        r'<meta\b[^>]*\bname\s*=\s*(["\'])theme-color\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "manifest": re.compile(
        r'<link\b[^>]*\brel\s*=\s*(["\'])manifest\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "apple_icon": re.compile(
        r'<link\b[^>]*\brel\s*=\s*(["\'])apple-touch-icon\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "pwa_icon": re.compile(
        r'<link\b[^>]*\brel\s*=\s*(["\'])(?:icon|shortcut icon)\1[^>]*'
        r'\bhref\s*=\s*(["\'])[^"\']*pwa-192\.png\2[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "mobile_capable": re.compile(
        r'<meta\b[^>]*\bname\s*=\s*(["\'])mobile-web-app-capable\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "apple_capable": re.compile(
        r'<meta\b[^>]*\bname\s*=\s*(["\'])apple-mobile-web-app-capable\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "apple_status": re.compile(
        r'<meta\b[^>]*\bname\s*=\s*(["\'])apple-mobile-web-app-status-bar-style\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "apple_title": re.compile(
        r'<meta\b[^>]*\bname\s*=\s*(["\'])apple-mobile-web-app-title\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "ux_css": re.compile(
        r'<link\b[^>]*\bhref\s*=\s*(["\'])[^"\']*assets/platform/platform-ux-v370\.css'
        r'(?:\?[^"\']*)?\1[^>]*>',
        re.IGNORECASE | re.DOTALL,
    ),
    "ux_js": re.compile(
        r'<script\b[^>]*\bsrc\s*=\s*(["\'])[^"\']*assets/platform/platform-ux-v370\.js'
        r'(?:\?[^"\']*)?\1[^>]*>\s*</script>',
        re.IGNORECASE | re.DOTALL,
    ),
}


def relative_prefix(path: Path, root: Path) -> str:
    return "../" * len(path.relative_to(root).parent.parts)


def is_verification(path: Path, root: Path, source: str) -> bool:
    return path.parent == root and bool(VERIFY_RE.match(source.strip()))


def production_html(root: Path):
    for path in sorted(root.rglob("*.html")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        yield path


def ensure_body_marker(source: str) -> tuple[str, bool]:
    match = BODY_OPEN_RE.search(source)
    if not match:
        return source, False
    attrs = match.group("attrs")
    marker_re = re.compile(
        r'\sdata-pt-ux-v370\s*=\s*(["\']).*?\1',
        re.IGNORECASE | re.DOTALL,
    )
    if marker_re.search(attrs):
        attrs = marker_re.sub(' data-pt-ux-v370="true"', attrs, count=1)
    else:
        attrs += ' data-pt-ux-v370="true"'
    return source[: match.start()] + f"<body{attrs}>" + source[match.end() :], True


def required_assets(root: Path) -> list[str]:
    required = [
        "manifest.webmanifest",
        "assets/brand/pwa-192.png",
        "assets/brand/pwa-512.png",
        "assets/brand/pwa-maskable-512.png",
        "assets/platform/platform-ux-v370.css",
        "assets/platform/platform-ux-v370.js",
    ]
    return [item for item in required if not (root / item).is_file()]


def normalize_file(path: Path, root: Path, *, check_only: bool) -> dict[str, str]:
    relative = path.relative_to(root).as_posix()
    source = path.read_text(encoding="utf-8")
    if is_verification(path, root, source):
        return {"path": relative, "status": "verification-skipped"}
    if not HEAD_CLOSE_RE.search(source):
        return {"path": relative, "status": "error", "detail": "missing </head>"}

    prefix = relative_prefix(path, root)
    tags = [
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
        '<meta name="theme-color" content="#075f5b">',
        f'<link rel="manifest" href="{prefix}manifest.webmanifest">',
        f'<link rel="icon" href="{prefix}assets/brand/pwa-192.png" sizes="192x192" type="image/png">',
        f'<link rel="apple-touch-icon" href="{prefix}assets/brand/pwa-192.png" sizes="192x192">',
        '<meta name="mobile-web-app-capable" content="yes">',
        '<meta name="apple-mobile-web-app-capable" content="yes">',
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">',
        '<meta name="apple-mobile-web-app-title" content="HealthRenewal">',
        f'<link rel="stylesheet" href="{prefix}assets/platform/platform-ux-v370.css?v={VERSION}">',
    ]
    if relative not in NO_UX_SCRIPT_PATHS:
        tags.append(
            f'<script defer src="{prefix}assets/platform/platform-ux-v370.js?v={VERSION}"></script>'
        )

    block = BLOCK_START + "\n" + "\n".join(tags) + "\n" + BLOCK_END
    existing_blocks = list(BLOCK_RE.finditer(source))
    if len(existing_blocks) > 1:
        return {"path": relative, "status": "error", "detail": "duplicate PWA UX blocks"}
    if existing_blocks:
        normalized = BLOCK_RE.sub("\n" + block + "\n", source, count=1)
    else:
        normalized = source
        for name, pattern in PATTERNS.items():
            if name == "ux_js" and relative in NO_UX_SCRIPT_PATHS:
                normalized = pattern.sub("", normalized)
                continue
            normalized = pattern.sub("", normalized)
        normalized = re.sub(r"\s*</head\s*>", "\n</head>", normalized, count=1, flags=re.IGNORECASE)
        normalized = HEAD_CLOSE_RE.sub(block + "\n</head>", normalized, count=1)
    normalized, has_body = ensure_body_marker(normalized)
    if not has_body:
        return {"path": relative, "status": "error", "detail": "missing <body>"}

    if normalized == source:
        return {"path": relative, "status": "current"}
    if check_only:
        return {"path": relative, "status": "needs-update"}
    path.write_text(normalized, encoding="utf-8", newline="\n")
    return {"path": relative, "status": "updated"}


def apply(
    root: Path,
    *,
    check_only: bool = False,
    report_path: Path | None = None,
) -> dict[str, object]:
    root = root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Site root not found: {root}")

    missing_assets = required_assets(root)
    if missing_assets:
        raise SystemExit({"missing_pwa_ux_assets": missing_assets})

    results = [
        normalize_file(path, root, check_only=check_only)
        for path in production_html(root)
    ]
    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1

    report = {
        "version": VERSION,
        "status": "failed" if counts.get("error", 0) else "passed",
        "mode": "check" if check_only else "write",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "counts": counts,
        "html_pages_seen": len(results),
        "assets_verified": not missing_assets,
        "strict_runtime_exclusions": sorted(NO_UX_SCRIPT_PATHS),
        "results": results,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if counts.get("error", 0):
        raise SystemExit(report)
    if check_only and counts.get("needs-update", 0):
        raise SystemExit(report)
    if not results:
        raise SystemExit("No production HTML pages found for PWA UX normalization")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize PWA and responsive UX metadata across production HTML."
    )
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report-path", type=Path)
    args = parser.parse_args()
    report = apply(
        args.root,
        check_only=args.check,
        report_path=args.report_path,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
