#!/usr/bin/env python3
"""Materialize the reviewed addiction-center publication payload.

This temporary helper reconstructs a tar.gz payload stored in deterministic
ASCII chunks, validates archive paths, and extracts the reviewed static-site
files into the repository root.
"""

from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = [ROOT / ".addiction-payload" / f"part{i:02d}" for i in range(5)]
ACTIVATION_VERSION = 2


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in PARTS if not path.exists()]
    if missing:
        raise SystemExit(f"Missing addiction payload parts: {missing}")

    encoded = "".join(path.read_text(encoding="ascii").strip() for path in PARTS)
    raw = base64.b64decode(encoded, validate=True)
    root_resolved = ROOT.resolve()

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            target = (ROOT / member.name).resolve()
            if target != root_resolved and root_resolved not in target.parents:
                raise SystemExit(f"Unsafe archive path: {member.name}")
        archive.extractall(ROOT, filter="data")

    digest = hashlib.sha256(raw).hexdigest()
    print({"status": "materialized", "activation": ACTIVATION_VERSION, "files": len(members), "sha256": digest})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
