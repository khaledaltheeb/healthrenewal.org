from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_SHA256 = "e2dad5f6b9b770ec428c70a566094e1d76bf8abb2985a0c77f59c320eb4c1cdd"
ARCHIVE_SHA256 = "036c2161a6eb4f3f2a97e89f2b70f42bbd1717dd5abf296f5ee70be1bfde6138"


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Required marker not found in {path}: {old[:160]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    chunks = sorted((ROOT / "tools").glob("specialist_identity_v6_payload.*"))
    if not chunks:
        raise SystemExit("Specialist identity v6 payload chunks were not found")

    payload = "".join(path.read_text(encoding="ascii").strip() for path in chunks)
    payload_hash = hashlib.sha256(payload.encode("ascii")).hexdigest()
    if payload_hash != PAYLOAD_SHA256:
        raise SystemExit(f"Payload checksum mismatch: {payload_hash}")

    archive = base64.b64decode(payload, validate=True)
    archive_hash = hashlib.sha256(archive).hexdigest()
    if archive_hash != ARCHIVE_SHA256:
        raise SystemExit(f"Archive checksum mismatch: {archive_hash}")

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            target = (ROOT / member.name).resolve()
            if target != ROOT and ROOT not in target.parents:
                raise SystemExit(f"Unsafe archive path: {member.name}")
            if member.issym() or member.islnk():
                raise SystemExit(f"Links are not allowed in the archive: {member.name}")
        tar.extractall(ROOT, filter="data")

    worker = ROOT / "specialists-partners" / "account-backend" / "src" / "index.js"
    replace_required(
        worker,
        "      if (request.method === 'POST' && url.pathname === '/v1/auth/logout') return await logout(env, cors, actor);\n",
        "      if (request.method === 'POST' && url.pathname === '/v1/auth/logout') return await logout(env, cors, actor);\n"
        "      if (request.method === 'POST' && url.pathname === '/v1/specialist/session/revoke') return await logout(env, cors, actor);\n",
    )

    legacy_tests = ROOT / "tests" / "test_specialist_accounts_v5.py"
    replace_required(
        legacy_tests,
        '        self.assertNotIn("password_hash", source)\n',
        '        self.assertIn("password_hash", source)\n',
    )
    replace_required(
        legacy_tests,
        '        self.assertIn("action:\'specialist_login\'", source)\n',
        '        self.assertIn("/v1/specialist/session/verify", source)\n',
    )
    replace_required(
        legacy_tests,
        '        self.assertNotIn(\'type="password"\', html)\n',
        '        self.assertIn(\'type="password"\', html)\n',
    )

    for path in chunks:
        path.unlink()
    Path(__file__).unlink()

    print("Specialist identity v6 materialized and compatibility checks updated.")


if __name__ == "__main__":
    main()
