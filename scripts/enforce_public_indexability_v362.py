#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

VERSION = 362
STANDARD_ROBOTS = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"

META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE | re.DOTALL)
HEAD_OPEN_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
REFRESH_RE = re.compile(
    r"<meta\b(?=[^>]*\bhttp-equiv\s*=\s*([\"'])refresh\1)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
X_ROBOTS_NOINDEX_RE = re.compile(
    r"x-robots-tag[^\n\r]*noindex", re.IGNORECASE
)

EXCLUDED_TOP_LEVEL = {
    ".git",
    ".github",
    ".pytest_cache",
    "node_modules",
    "tests",
    "reports",
    "tmp",
    "vendor",
}

# These routes are intentionally not search landing pages. They are private,
# transactional, stateful, or query-driven application shells.
EXPLICIT_TECHNICAL_NOINDEX = {
    "404.html",
    "addiction/substances/view/index.html",
    "specialists-partners/contact.html",
    "specialists-partners/account/index.html",
    "specialists-partners/admin/index.html",
    "specialists-partners/portal/index.html",
    "specialists-partners/recover/index.html",
    "specialists-partners/password-reset/index.html",
}

HEADER_CONFIG_NAMES = {"_headers", "headers", "wrangler.toml", "wrangler.json", "wrangler.jsonc"}


def attr(tag: str, name: str) -> str:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*([\"'])(.*?)\1",
        tag,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(2).strip() if match else ""


def is_verification_file(relative: str) -> bool:
    path = Path(relative)
    if path.parent != Path("."):
        return False
    name = path.name.lower()
    return bool(
        re.fullmatch(r"google[a-z0-9_-]+\.html", name)
        or re.fullmatch(r"bing[a-z0-9_-]+\.html", name)
        or re.fullmatch(r"yandex_[a-z0-9_-]+\.html", name)
        or re.fullmatch(r"baidu_verify_[a-z0-9_-]+\.html", name)
    )


def technical_reason(relative: str, source: str) -> str | None:
    if relative in EXPLICIT_TECHNICAL_NOINDEX:
        return "explicit-technical"
    if is_verification_file(relative):
        return "search-verification"
    # Legacy aliases redirect immediately to their canonical replacement. Keeping
    # the alias noindex prevents duplicate search results while the target remains indexed.
    if REFRESH_RE.search(source):
        return "redirect-alias"
    return None


def robots_meta(source: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in META_TAG_RE.finditer(source):
        tag = match.group(0)
        name = attr(tag, "name").lower()
        if name in {"robots", "googlebot"}:
            found.append((name, attr(tag, "content").lower()))
    return found


def contains_noindex(source: str) -> bool:
    return any("noindex" in content for _, content in robots_meta(source))


def has_explicit_index(source: str) -> bool:
    metas = robots_meta(source)
    if not metas:
        return False
    return any(
        name == "robots" and "index" in {token.strip() for token in content.split(",")}
        for name, content in metas
    )


def normalize_public_robots(source: str) -> tuple[str, bool, bool]:
    changed = False
    removed_noindex = False
    saw_robots = False

    def replace_meta(match: re.Match[str]) -> str:
        nonlocal changed, removed_noindex, saw_robots
        tag = match.group(0)
        name = attr(tag, "name").lower()
        if name not in {"robots", "googlebot"}:
            return tag
        if name == "robots":
            saw_robots = True
        content = attr(tag, "content").lower()
        if "noindex" in content:
            removed_noindex = True
        desired = f'<meta name="{name}" content="{STANDARD_ROBOTS}">'
        if tag != desired:
            changed = True
            return desired
        return tag

    updated = META_TAG_RE.sub(replace_meta, source)
    if not saw_robots:
        marker = HEAD_OPEN_RE.search(updated)
        if marker:
            insertion = marker.end()
            updated = updated[:insertion] + f'\n<meta name="robots" content="{STANDARD_ROBOTS}">' + updated[insertion:]
            changed = True
    return updated, changed, removed_noindex


def robots_allows_public_crawl(root: Path) -> tuple[bool, list[str]]:
    path = root / "robots.txt"
    if not path.is_file():
        return False, ["robots.txt missing"]
    text = path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    errors: list[str] = []
    if "user-agent: *" not in lowered:
        errors.append("robots.txt missing User-agent: *")
    if "allow: /" not in lowered:
        errors.append("robots.txt missing Allow: /")
    # A site-wide Disallow overrides the publication goal even if page metadata says index.
    for line in text.splitlines():
        stripped = line.strip().lower()
        if stripped in {"disallow: /", "disallow:/"}:
            errors.append("robots.txt contains site-wide Disallow: /")
    return not errors, errors


def x_robots_blocks(root: Path) -> list[str]:
    blocks: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_TOP_LEVEL for part in relative.parts):
            continue
        if path.name not in HEADER_CONFIG_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if X_ROBOTS_NOINDEX_RE.search(text):
            blocks.append(relative.as_posix())
    return sorted(blocks)


def audit(root: Path, *, fix: bool = False, report_path: Path | None = None) -> tuple[dict[str, object], bool]:
    root = root.resolve()
    counters: Counter[str] = Counter()
    public_noindex_before: list[str] = []
    public_noindex_after: list[str] = []
    public_without_explicit_index: list[str] = []
    fixed_noindex: list[str] = []
    stamped_index: list[str] = []
    exemptions: list[dict[str, str]] = []

    for page in sorted(root.rglob("*.html")):
        relative_path = page.relative_to(root)
        if any(part in EXCLUDED_TOP_LEVEL for part in relative_path.parts):
            continue
        relative = relative_path.as_posix()
        source = page.read_text(encoding="utf-8", errors="strict")
        counters["html_pages_scanned"] += 1

        reason = technical_reason(relative, source)
        if reason:
            counters[f"exempt_{reason}"] += 1
            exemptions.append({"path": relative, "reason": reason})
            continue

        counters["public_pages"] += 1
        if contains_noindex(source):
            public_noindex_before.append(relative)

        if fix:
            updated, changed, removed_noindex = normalize_public_robots(source)
            if changed:
                page.write_text(updated, encoding="utf-8")
                source = updated
                stamped_index.append(relative)
            if removed_noindex:
                fixed_noindex.append(relative)

        if contains_noindex(source):
            public_noindex_after.append(relative)
        if not has_explicit_index(source):
            public_without_explicit_index.append(relative)

    crawl_ok, robots_errors = robots_allows_public_crawl(root)
    header_blocks = x_robots_blocks(root)
    status = "passed" if not public_noindex_after and crawl_ok and not header_blocks else "failed"

    report: dict[str, object] = {
        "version": VERSION,
        "status": status,
        "policy": "all public canonical content pages indexable; only technical/private/redirect routes may remain noindex",
        "counts": dict(sorted(counters.items())),
        "public_noindex_before": public_noindex_before,
        "public_noindex_after": public_noindex_after,
        "public_without_explicit_index": public_without_explicit_index,
        "fixed_noindex": fixed_noindex,
        "stamped_index": stamped_index,
        "robots_txt_allows_public_crawl": crawl_ok,
        "robots_txt_errors": robots_errors,
        "x_robots_noindex_config_files": header_blocks,
        "technical_exemptions": exemptions,
    }

    if report_path is not None:
        target = report_path if report_path.is_absolute() else root / report_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return report, status == "passed"


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce public page indexability while preserving technical noindex routes")
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--fix", action="store_true", help="replace accidental public noindex and stamp explicit index,follow metadata")
    parser.add_argument("--report", type=Path, default=Path("api/public-indexability-v362.json"))
    args = parser.parse_args()

    report, passed = audit(args.root, fix=args.fix, report_path=args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
