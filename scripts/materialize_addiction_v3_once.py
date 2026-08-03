from __future__ import annotations
import base64
import hashlib
import io
import lzma
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "content" / "addiction-v3-static.tar.xz.b64"
EXPECTED_XZ_SHA256 = "2c9be86aa72ba3b828cd04541a4ff5c804524e807a285eced5086af9bf437db4"
EXPECTED_TAR_SHA256 = "17c314c6a87e229157c2d8dd5932cb1aad136a81577ecfe28d5aaa55be5a1f8b"
EXPECTED_MEMBERS = ['addiction/alcohol-use-disorder/index.html', 'addiction/cannabis-use-disorder/index.html', 'addiction/conditions/index.html', 'addiction/editorial-manifest-v3.json', 'addiction/gambling-related-harms/index.html', 'addiction/gaming-disorder/index.html', 'addiction/index.html', 'addiction/inhalant-use-disorder/index.html', 'addiction/methodology/index.html', 'addiction/nicotine-tobacco-dependence/index.html', 'addiction/opioid-use-disorder/index.html', 'addiction/polysubstance-use-and-overdose-risk/index.html', 'addiction/sedative-benzodiazepine-use-disorder/index.html', 'addiction/stimulant-use-disorder/index.html', 'api/addiction-condition-guides-v3.json', 'assets/addiction/condition-guides-v3.css', 'sitemap-addiction.xml', 'tests/test_addiction_condition_guides_v3.py']

def main() -> None:
    encoded = "".join(PAYLOAD.read_text(encoding="ascii").split())
    compressed = base64.b64decode(encoded, validate=True)
    if hashlib.sha256(compressed).hexdigest() != EXPECTED_XZ_SHA256:
        raise SystemExit("Addiction v3 payload XZ checksum mismatch")
    raw = lzma.decompress(compressed)
    if hashlib.sha256(raw).hexdigest() != EXPECTED_TAR_SHA256:
        raise SystemExit("Addiction v3 payload TAR checksum mismatch")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        members = [m for m in archive.getmembers() if m.isfile()]
        names = sorted(m.name for m in members)
        if names != EXPECTED_MEMBERS:
            raise SystemExit("Addiction v3 payload member manifest mismatch")
        for member in members:
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts:
                raise SystemExit(f"Unsafe archive member: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise SystemExit(f"Unreadable archive member: {member.name}")
            target = ROOT.joinpath(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read())
    print(f"Materialized {len(EXPECTED_MEMBERS)} addiction v3 static files")

if __name__ == "__main__":
    main()
