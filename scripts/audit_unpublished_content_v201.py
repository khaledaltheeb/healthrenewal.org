#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

try:
    import audit_unpublished_content_v201_core as core
    from audit_unpublished_content_v201_core import *  # noqa: F401,F403
except ModuleNotFoundError:
    from scripts import audit_unpublished_content_v201_core as core
    from scripts.audit_unpublished_content_v201_core import *  # noqa: F401,F403

# Base64 text parts are source content, not opaque binary assets. Extend the
# established v201 graph rather than bypassing it with a separate audit.
core.TEXT_EXTENSIONS.add(".b64")
core.DIRECT_PATH_RE = re.compile(
    core.DIRECT_PATH_RE.pattern.replace("webmanifest", "webmanifest|b64")
)
core.WITH_NAME_RE = re.compile(
    core.WITH_NAME_RE.pattern.replace("webmanifest", "webmanifest|b64")
)
_original_is_candidate = core.is_candidate


def is_candidate(root: Path, path: Path) -> bool:
    parts = path.relative_to(root).parts
    if parts and parts[0] == "content" and path.suffix.lower() == ".b64":
        return True
    return _original_is_candidate(root, path)


core.is_candidate = is_candidate
TEXT_EXTENSIONS = core.TEXT_EXTENSIONS
DIRECT_PATH_RE = core.DIRECT_PATH_RE
WITH_NAME_RE = core.WITH_NAME_RE
main = core.main


if __name__ == "__main__":
    raise SystemExit(main())
