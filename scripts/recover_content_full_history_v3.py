#!/usr/bin/env python3
from __future__ import annotations

"""Run the established recovery engine against every distinct Git page version.

The underlying recovery scorer rewards substantive editorial structure and
penalizes repetitive/template content. This entrypoint broadens the historical
candidate pool from a small representative sample to every distinct HTML blob
reachable from the fetched Git refs, while preventing obsolete
operational/prototype surfaces from being resurrected merely because an old
variant is longer.

It also enforces a hard no-shortening rule for routes already present in the
assembled site. A historical/baseline candidate may score better structurally,
but it is never allowed to replace an existing page with fewer visible words.
The richer existing page remains the base; unique historical material must be
merged separately rather than recovered by destructive replacement.
"""

from collections import defaultdict
from pathlib import Path

import recover_content_v1 as base

_original_history = base.history
_original_safe = base.safe

# These routes are historical implementation/admin surfaces, not public
# editorial content. Existing copies in the validated production baseline are
# left untouched; only resurrection from Git history is blocked.
HISTORICAL_RESTORE_BLOCKED_PREFIXES = (
    'professional-assessment-hub/',
    'provider-assessment-platform/',
    'specialists-partners/admin/',
    'specialists-partners/portal/',
)


def recovery_safe(path: str) -> bool:
    normalized = path.replace('\\', '/').lstrip('/')
    return _original_safe(path) and not normalized.startswith(HISTORICAL_RESTORE_BLOCKED_PREFIXES)


def _parse_distinct_history(raw: str) -> dict[str, list[str]]:
    """Return every distinct reachable HTML version, deduplicated by Git blob.

    ``git log --raw`` exposes the post-change blob id for each A/M event. The
    same file content can occur in many commits or branches; comparing it again
    adds cost but no editorial information. We therefore keep the newest commit
    that exposes each distinct blob for a path and retain *all* distinct blobs,
    rather than sampling only the first/high-churn 24 commits.
    """
    commit = ''
    seen_blobs: dict[str, set[str]] = defaultdict(set)
    versions: dict[str, list[str]] = defaultdict(list)

    for line in raw.splitlines():
        if line.startswith('@@'):
            commit = line[2:].strip()
            continue
        if not commit or not line.startswith(':') or '\t' not in line:
            continue

        metadata, path = line.split('\t', 1)
        fields = metadata.split()
        if len(fields) < 5:
            continue
        new_blob = fields[3]
        status = fields[4]
        if not status.startswith(('A', 'M')):
            continue
        if not new_blob or set(new_blob) == {'0'} or not recovery_safe(path):
            continue
        if new_blob in seen_blobs[path]:
            continue

        seen_blobs[path].add(new_blob)
        versions[path].append(commit)

    return dict(versions)


def full_history_candidates(since: str, limit: int = 24):
    """Enumerate every distinct HTML/HTM blob across all fetched Git refs.

    ``since`` is intentionally honored to preserve the caller's configured
    history horizon (production currently supplies 3650 days), but ``limit`` is
    intentionally ignored: limiting to 24 representative commits can miss the
    richest version of a page. Distinct-blob deduplication prevents repeated
    identical versions from inflating the comparison set.
    """
    raw = base.git([
        'log', '--all', f'--since={since}', '--no-renames', '--diff-filter=AM',
        '--raw', '--format=@@%H', '--', '*.html', '*.htm',
    ])
    parsed = _parse_distinct_history(raw)
    if parsed:
        return parsed

    # Defensive fallback for unusual Git output. Keep the previous widened
    # representative scan rather than disabling historical recovery entirely.
    return _original_history(since, limit=max(limit, 24))


# recover_content_v2 imports this same module object as ``b``. Monkeypatching
# before importing v2 applies both the exhaustive distinct-version scan and the
# public-surface guard while preserving the established scoring/consolidation
# implementation.
base.safe = recovery_safe
base.history = full_history_candidates

import recover_content_v2 as recovery  # noqa: E402

recovery.b.safe = recovery_safe
recovery.b.history = full_history_candidates

_original_restore = recovery.restore


def restore_without_shortening(site: Path, since: str, baseline: Path | None):
    """Run historical recovery while forbidding destructive page shortening.

    ``recover_content_v2.restore`` can choose a candidate whose structural
    score is >= 8% better even when that candidate has fewer words. That is a
    useful editorial signal, but it is not a safe replacement rule for content
    recovery. Snapshot every current HTML route first, run the established
    recovery selection, then roll back only replacements that reduced the word
    count of an already-present page.

    New/missing routes remain recoverable. Equal-or-longer replacements remain
    eligible. Shorter historical variants can still be reviewed later and have
    unique material merged into the richer current page deliberately.
    """
    site = Path(site)
    current_content: dict[str, str] = {}
    for file in base.html_files(site):
        path = file.relative_to(site).as_posix()
        current_content[path] = file.read_text(encoding='utf-8', errors='replace')

    restored = _original_restore(site, since, baseline)
    accepted = []
    blocked = []
    for item in restored:
        path = item.get('path', '')
        previous_words = int(item.get('previousWords') or 0)
        restored_words = int(item.get('restoredWords') or 0)
        previous = current_content.get(path)
        if previous is not None and restored_words < previous_words:
            destination = site / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(previous, encoding='utf-8')
            blocked.append({
                **item,
                'decision': 'blocked-shortening',
                'reason': 'historical candidate is shorter than the existing page',
            })
            continue
        accepted.append(item)

    if blocked:
        print({
            'noShorteningGuard': 'passed',
            'blockedHistoricalReplacements': len(blocked),
            'paths': [item['path'] for item in blocked],
        })
    return accepted


recovery.restore = restore_without_shortening


if __name__ == '__main__':
    recovery.main()
