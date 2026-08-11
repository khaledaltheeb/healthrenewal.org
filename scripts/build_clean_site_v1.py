#!/usr/bin/env python3
"""Clean production build: current main wins; baseline may restore missing files only."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import normalize_platform_shell as shell

SKIP = {
    '.git', '.github', '_site', '_baseline', '_legacy_baseline', 'node_modules',
    '.venv', 'venv', 'tests', 'reports', '__pycache__', '.pytest_cache',
}


def copy_tree(root: Path, site: Path, *, missing_only: bool) -> int:
    count = 0
    if not root or not root.exists():
        return 0
    for current, dirs, files in os.walk(root):
        base = Path(current)
        rel = base.relative_to(root)
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('.git')]
        if any(part in SKIP for part in rel.parts):
            continue
        for name in files:
            src = base / name
            rp = src.relative_to(root)
            if any(part in SKIP for part in rp.parts) or src.is_symlink():
                continue
            dst = site / rp
            if missing_only and dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            count += 1
    return count


def remove_generated_mixes(site: Path) -> dict[str, int]:
    patterns = (
        re.compile(r'\s*<section\b[^>]*class=["\'][^"\']*historical-content-merge[^"\']*["\'][^>]*>.*?</section>\s*', re.I | re.S),
        re.compile(r'\s*<section\b[^>]*class=["\'][^"\']*merged-duplicate-content[^"\']*["\'][^>]*>.*?</section>\s*', re.I | re.S),
        re.compile(r'\s*<section\b[^>]*class=["\'][^"\']*content-recovery-related[^"\']*["\'][^>]*>.*?</section>\s*', re.I | re.S),
    )
    changed = 0
    removed = 0
    for page in sorted(site.rglob('*.html')):
        source = page.read_text(encoding='utf-8', errors='replace')
        updated = source
        page_removed = 0
        for pattern in patterns:
            updated, n = pattern.subn('\n', updated)
            page_removed += n
        if updated != source:
            page.write_text(updated, encoding='utf-8', newline='\n')
            changed += 1
            removed += page_removed
    return {'pagesCleaned': changed, 'generatedMixBlocksRemoved': removed}


def inject_polish(site: Path) -> int:
    changed = 0
    for page in sorted(site.rglob('*.html')):
        source = page.read_text(encoding='utf-8', errors='replace')
        if '</head' not in source.lower() or 'sitewide-polish.css?v=1' in source:
            continue
        prefix = '../' * len(page.relative_to(site).parent.parts)
        tag = f'<link rel="stylesheet" href="{prefix}assets/platform/sitewide-polish.css?v=1">\n'
        updated = re.sub(r'</head\s*>', tag + '</head>', source, count=1, flags=re.I)
        if updated != source:
            page.write_text(updated, encoding='utf-8', newline='\n')
            changed += 1
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--site', default='_site')
    parser.add_argument('--baseline', default='')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    site = Path(args.site).resolve()
    baseline = Path(args.baseline).resolve() if args.baseline else None
    shutil.rmtree(site, ignore_errors=True)
    site.mkdir(parents=True)

    main_files = copy_tree(root, site, missing_only=False)
    baseline_files = copy_tree(baseline, site, missing_only=True) if baseline else 0
    if not (site / 'index.html').is_file():
        raise SystemExit('index.html missing from current main')

    cleanup = remove_generated_mixes(site)
    runtime = shell.copy_platform_runtime(site)
    results = [shell.normalize_file(path, site, check_only=False) for path in shell.production_html_files(site)]
    errors = [item for item in results if item.status == 'error']
    if errors:
        raise SystemExit({'normalizationErrors': [item.path for item in errors[:20]]})
    polished = inject_polish(site)

    html_pages = sum(1 for _ in site.rglob('*.html'))
    report = {
        'schemaVersion': 2,
        'status': 'passed',
        'policy': 'current-main pages are authoritative; baseline restores missing paths only; no cross-page or historical fragment merging',
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'mainFilesCopied': main_files,
        'baselineMissingFilesRestored': baseline_files,
        'htmlPages': html_pages,
        'pagesCleaned': cleanup['pagesCleaned'],
        'generatedMixBlocksRemoved': cleanup['generatedMixBlocksRemoved'],
        'pagesPolished': polished,
        'platformRuntimeFilesCopied': len(runtime.get('files', [])),
    }
    api = site / 'api'
    api.mkdir(parents=True, exist_ok=True)
    (api / 'clean-site-build-v1.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (site / '.nojekyll').touch()
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
