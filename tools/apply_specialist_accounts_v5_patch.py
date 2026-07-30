from __future__ import annotations

import base64
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Required marker not found in {path}: {old[:120]}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    chunk_paths = sorted((ROOT / "tools").glob("specialist_accounts_v5_payload.*"))
    if not chunk_paths:
        raise SystemExit("Patch payload chunks were not found")
    payload = "".join(path.read_text(encoding="ascii").strip() for path in chunk_paths)
    archive = base64.b64decode(payload, validate=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            target = (ROOT / member.name).resolve()
            if ROOT not in target.parents and target != ROOT:
                raise SystemExit(f"Unsafe archive path: {member.name}")
        tar.extractall(ROOT, filter="data")

    directory = ROOT / "specialists-partners" / "index.html"
    replace_required(
        directory,
        '<a href="join.html">الانضمام للشبكة</a><a href="portal/">بوابة المحادثات</a>',
        '<a href="join.html">الانضمام للشبكة</a><a href="account/">حساب المختص</a><a href="portal/">بوابة المحادثات</a>',
    )
    replace_required(
        directory,
        '<a class="button secondary" href="join.html">إضافة مختص أو مركز</a></div>',
        '<a class="button secondary" href="join.html">إضافة مختص أو مركز</a><a class="button secondary" href="account/">دخول المختصين</a></div>',
    )

    join = ROOT / "specialists-partners" / "join.html"
    replace_required(
        join,
        '<a href="join.html" aria-current="page">الانضمام</a><a href="portal/">بوابة المحادثة</a>',
        '<a href="join.html" aria-current="page">الانضمام</a><a href="account/">حساب المختص</a><a href="portal/">بوابة المحادثة</a>',
    )

    marker = '               f"  apiBase: {json.dumps(api)},\\n"\n'
    account_line = '               \'  accountApiBase: "https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev",\\n\'\n'
    for relative in (
        ".github/workflows/bootstrap-specialists-cloudflare.yml",
        ".github/workflows/deploy-specialists-backend.yml",
    ):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        if "accountApiBase" not in text:
            if marker not in text:
                raise SystemExit(f"Runtime config marker not found in {path}")
            path.write_text(text.replace(marker, marker + account_line), encoding="utf-8")

    for path in chunk_paths:
        path.unlink()
    for relative in (
        "tools/apply_specialist_accounts_v5_patch.py",
        ".github/workflows/apply-specialist-accounts-v5.yml",
    ):
        path = ROOT / relative
        if path.exists():
            path.unlink()


if __name__ == "__main__":
    main()
