#!/usr/bin/env python3
from __future__ import annotations

"""Run the existing recovery engine with a wider historical candidate set.

The v1 history collector is intentionally reused because it already penalizes
repetitive/template content and measures semantic/editorial structure.  The
legacy default keeps only four commit candidates for every route; that is too
narrow for a repository with hundreds of long-lived content branches.  This
entrypoint widens the candidate set without forking the scoring/consolidation
logic.
"""

import recover_content_v1 as base

_original_history = base.history


def full_history_candidates(since: str, limit: int = 24):
    # 24 representative versions per route is broad enough to include early,
    # recent and high-change candidates while avoiding an unbounded cartesian
    # scan of thousands of generated revisions.
    return _original_history(since, limit=max(limit, 24))


# recover_content_v2 imports this same module object as ``b``. Monkeypatching
# before importing v2 makes every historical lookup in the recovery process use
# the wider candidate set while preserving the established quality metrics.
base.history = full_history_candidates

import recover_content_v2 as recovery  # noqa: E402

recovery.b.history = full_history_candidates


if __name__ == '__main__':
    recovery.main()
