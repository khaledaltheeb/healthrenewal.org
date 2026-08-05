#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
import recover_content_v2 as v

GENERIC_SLUGS = {'index','about','privacy','terms','methodology','transition','support','guide','path','angle'}


def slug(path: str) -> str:
    pure = PurePosixPath(path)
    parts = list(pure.parts)
    if parts and parts[-1] in {'index.html', 'index.htm'}:
        parts.pop()
    return parts[-1].lower() if parts else ''


def slug_tokens(value: str) -> set[str]:
    return {token for token in re.split(r'[-_]+', value.lower()) if len(token) > 2 and token not in GENERIC_SLUGS}


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


def best_original(path: str, baseline: Path | None, history: dict[str, list[str]]):
    candidates = []
    head = v.b.show('HEAD', path)
    if head:
        metric = v.b.metrics(path, head)
        if not metric['redirect']:
            candidates.append(('HEAD', head, metric))
    if baseline and (baseline / path).is_file():
        text = (baseline / path).read_text(encoding='utf-8', errors='replace')
        metric = v.b.metrics(path, text)
        if not metric['redirect']:
            candidates.append(('validated-baseline', text, metric))
    for commit in history.get(path, []):
        text = v.b.show(commit, path)
        if text:
            metric = v.b.metrics(path, text)
            if not metric['redirect']:
                candidates.append((commit, text, metric))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[2]['score'], item[2]['words'], item[2]['sections'], item[2]['bytes']))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='_site')
    parser.add_argument('--baseline', default='')
    parser.add_argument('--days', type=int, default=10)
    args = parser.parse_args()
    site = Path(args.site).resolve()
    baseline = Path(args.baseline).resolve() if args.baseline else None
    report_path = site / 'api/content-recovery-report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    aliases = list(report.get('aliases', []))
    since = (datetime.now(timezone.utc) - timedelta(days=max(args.days, 7))).date().isoformat()
    history = v.b.history(since)
    retained, rejected, unrestored = [], [], []

    for alias in aliases:
        source = alias['path']
        target = alias['target']
        if safe_alias(source, target):
            retained.append(alias)
            continue
        original = best_original(source, baseline, history)
        if original is None:
            unrestored.append(alias)
            continue
        origin, text, metric = original
        destination = site / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')
        rejected.append({
            **alias,
            'restoredFrom': origin,
            'restoredWords': metric['words'],
            'reason': 'different semantic slug; expanded as an independent page instead of redirecting',
        })

    report['aliases'] = retained
    report['thinAliasesRedirected'] = len(retained)
    report['falseAliasesRejected'] = len(rejected)
    report['rejectedAliases'] = rejected
    report['unrestoredRejectedAliases'] = unrestored
    report['aliasReviewStatus'] = 'passed' if not unrestored else 'needs_review'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
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
