#!/usr/bin/env python3
from __future__ import annotations

"""Run the established recovery engine against the repository's full history.

The underlying recovery scorer already rewards substantive editorial structure
and penalizes repetitive/template content. This entrypoint broadens the
historical candidate pool while preventing obsolete operational/prototype
surfaces from being resurrected merely because an old variant is longer.
"""

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


def full_history_candidates(since: str, limit: int = 24):
    # 24 representative versions per route covers early, recent, and
    # high-change candidates without an unbounded scan of every generated
    # revision in a repository with hundreds of long-lived branches.
    return _original_history(since, limit=max(limit, 24))


# recover_content_v2 imports this same module object as ``b``. Monkeypatching
# before importing v2 applies both the wider history scan and the public-surface
# guard while preserving the established scoring/consolidation implementation.
base.safe = recovery_safe
base.history = full_history_candidates

import recover_content_v2 as recovery  # noqa: E402

recovery.b.safe = recovery_safe
recovery.b.history = full_history_candidates


if __name__ == '__main__':
    recovery.main()
