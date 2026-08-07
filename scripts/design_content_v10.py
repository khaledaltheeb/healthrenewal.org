#!/usr/bin/env python3
"""Run the preserved v10 design stage without overlaying legacy executable source.

The v10 implementation is retained in `.v10bundle` for reproducibility/history.
This tracked bridge extracts only that one historical executable into /tmp and
runs it with the caller's arguments.  It deliberately does not extract the
bundle over the checked-out repository, so PR validation remains bound to the
Git Head SHA.
"""
from __future__ import annotations

import base64
import io
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = [ROOT / ".v10bundle" / f"part0{i}" for i in range(5)]
MEMBER = "scripts/design_content_v10.py"
TARGET_ROOT = Path("/tmp/healthrenewal-v10-design")
TARGET = TARGET_ROOT / MEMBER


def _read_bundle() -> bytes:
    encoded = b"".join(part.read_bytes() for part in PARTS)
    return base64.b64decode(encoded, validate=True)


def _extract_exact_member(bundle: bytes) -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as archive:
        try:
            member = archive.getmember(MEMBER)
        except KeyError as exc:
            raise SystemExit(f"Required preserved v10 member is missing: {MEMBER}") from exc
        if not member.isfile():
            raise SystemExit(f"Preserved v10 member is not a regular file: {MEMBER}")
        source = archive.extractfile(member)
        if source is None:
            raise SystemExit(f"Could not read preserved v10 member: {MEMBER}")
        TARGET.write_bytes(source.read())


def main() -> int:
    bundle = _read_bundle()
    _extract_exact_member(bundle)
    command = [sys.executable, str(TARGET), *sys.argv[1:]]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
