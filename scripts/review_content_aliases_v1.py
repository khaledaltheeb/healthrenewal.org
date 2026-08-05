#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import recover_content_v2 as v

GENERIC_SLUGS = {
    'index', 'about', 'privacy', 'terms', 'methodology',
    'transition', 'support', 'guide', 'path', 'angle'
}
MERGE_MARKERS = (
    'دُمج محتوى هذه الصفحة',
    'دُمجت هذه الصفحة',
    'content-recovery-redirect',
)
CANONICAL_PATTERNS = (
    re.compile(r'<link\b[^>]*\brel=["\']canonical["\'][^>]*\bhref=["\']([^"\']+)', re.I),
    re.compile(r'<link\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*\brel=["\']canonical["\']', re.I),
)
REFRESH_PATTERN = re.compile(
    r'<meta\b[^>]*http-equiv=["\']refresh["\'][^>]*content=["\'][^"\']*url=([^"\'>\s;]+)',
    re.I,
)


def slug(path: str) -> str:
    pure = PurePosixPath(urlsplit(path).path.lstrip('/'))
    parts = list(pure.parts)
    if parts and parts[-1] in {'index.html', 'index.htm'}:
        parts.pop()
    return parts[-1].lower() if parts else ''


def slug_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.split(r'[-_]+', value.lower())
        if len(token) > 2 and token not in GENERIC_SLUGS
    }


def safe_alias(source: str, target: str) -> bool:
    source_slug = slug(source)
    target_slug = slug(target)
    if not source_slug or not target_slug:
        return False
    if source_slug == target_slug and source_slug not in GENERIC_SLUGS:
        return True
    source_tokens = slug_tokens(source_slug)
    target_tokens = slug_tokens(target_slug)
    return bool(source_tokens) and source_tokens == target_tokens and len(source_tokens) >= 2


def redirect_target(text: str) -> str:
    for pattern in CANONICAL_PATTERNS:
        match = pattern.search(text)
        if match:
            return html.unescape(match.group(1)).strip()
    match = REFRESH_PATTERN.search(text)
    return html.unescape(match.group(1)).strip() if match else ''


def generated_aliases(site: Path) -> list[dict]:
    aliases = []
    for page in v.b.html_files(site):
        text = page.read_text(encoding='utf-8', errors='replace')
        if not v.b.REDIR.search(text):
            continue
        if not any(marker in text for marker in MERGE_MARKERS):
            continue
        source = page.relative_to(site).as_posix()
        target = redirect_target(text)
        aliases.append({
            'path': source,
            'target': target,
            'previousWords': v.b.metrics(source, text)['words'],
            'inherited': True,
        })
    return aliases


def add_candidate(candidates: list, label: str, path: Path, source_path: str) -> None:
    candidate = path / source_path
    if not candidate.is_file():
        return
    text = candidate.read_text(encoding='utf-8', errors='replace')
    metric = v.b.metrics(source_path, text)
    if not metric['redirect']:
        candidates.append((label, text, metric))


def best_original(
    path: str,
    baseline: Path | None,
    legacy_baseline: Path | None,
    history: dict[str, list[str]],
):
    candidates = []
    head = v.b.show('HEAD', path)
    if head:
        metric = v.b.metrics(path, head)
        if not metric['redirect']:
            candidates.append(('HEAD', head, metric))

    if baseline:
        add_candidate(candidates, 'validated-baseline', baseline, path)
    if legacy_baseline:
        add_candidate(candidates, 'pre-merge-validated-baseline', legacy_baseline, path)

    for commit in history.get(path, []):
        text = v.b.show(commit, path)
        if text:
            metric = v.b.metrics(path, text)
            if not metric['redirect']:
                candidates.append((commit, text, metric))

    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item[2]['score'],
            item[2]['words'],
            item[2]['sections'],
            item[2]['bytes'],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='_site')
    parser.add_argument('--baseline', default='')
    parser.add_argument('--legacy-baseline', default='')
    parser.add_argument('--days', type=int, default=10)
    args = parser.parse_args()

    site = Path(args.site).resolve()
    baseline = Path(args.baseline).resolve() if args.baseline else None
    legacy_baseline = (
        Path(args.legacy_baseline).resolve() if args.legacy_baseline else None
    )
    report_path = site / 'api/content-recovery-report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))

    reported = {
        item['path']: item
        for item in report.get('aliases', [])
        if item.get('path')
    }
    for item in generated_aliases(site):
        reported[item['path']] = {**reported.get(item['path'], {}), **item}
    aliases = list(reported.values())

    since = (
        datetime.now(timezone.utc) - timedelta(days=max(args.days, 7))
    ).date().isoformat()
    history = v.b.history(since)
    retained, rejected, unrestored = [], [], []

    for alias in sorted(aliases, key=lambda item: item['path']):
        source = alias['path']
        target = alias.get('target', '')
        if safe_alias(source, target):
            retained.append(alias)
            continue

        original = best_original(
            source,
            baseline=baseline,
            legacy_baseline=legacy_baseline,
            history=history,
        )
        if original is None:
            unrestored.append({
                **alias,
                'reason': 'no independent non-redirect version was available',
            })
            continue

        origin, text, metric = original
        destination = site / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')
        rejected.append({
            **alias,
            'restoredFrom': origin,
            'restoredWords': metric['words'],
            'reason': (
                'different semantic slug; restored as an independent page '
                'instead of redirecting'
            ),
        })

    report['aliases'] = retained
    report['allGeneratedAliasesReviewed'] = len(aliases)
    report['thinAliasesRedirected'] = len(retained)
    report['falseAliasesRejected'] = len(rejected)
    report['rejectedAliases'] = rejected
    report['unrestoredRejectedAliases'] = unrestored
    report['aliasReviewStatus'] = 'passed' if not unrestored else 'needs_review'
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    print(json.dumps({
        'aliasesReviewed': len(aliases),
        'safeAliasesRetained': len(retained),
        'falseAliasesRejected': len(rejected),
        'unrestored': len(unrestored),
        'retained': retained,
    }, ensure_ascii=False))

    if unrestored:
        raise SystemExit({'unrestoredRejectedAliases': unrestored})


if __name__ == '__main__':
    main()
