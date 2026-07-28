from __future__ import annotations

import base64
import gzip
import hashlib
import py_compile
import subprocess
import sys
from pathlib import Path

PARTS = [
    ('.expander-v9/part00', 6000, '828683b0f49107616e2c1d4c7ff11a88c81243d62d2b96e28ba11209563fcfd5'),
    ('.expander-v9/part01', 6000, '6710908d42fbd52773fa9b0b10f7024fd6d824b322cdfae89c6a69ab9335e1d3'),
    ('.expander-v9/part02', 4478, '05311036b958191156cc9eab4c75557552319c61d9ae4a95e9886e197c40ad47'),
]
ENCODED_SHA256 = 'c703fb722909f77de222e3173eda4e59fbf3abb4d4fa25e893dd34ac03ed661a'
SOURCE_SHA256 = 'e869233832c07db64942c02f39046d4ccf330295e57ebc4ab5cdb1192588bbf3'

chunks = []
for filename, expected_size, expected_sha in PARTS:
    data = Path(filename).read_bytes()
    if len(data) != expected_size:
        raise SystemExit(f'{filename}: size {len(data)} != {expected_size}')
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        raise SystemExit(f'{filename}: sha256 mismatch {digest}')
    chunks.append(data)

encoded = b''.join(chunks)
if hashlib.sha256(encoded).hexdigest() != ENCODED_SHA256:
    raise SystemExit('combined Base85 payload SHA-256 mismatch')

source = gzip.decompress(base64.b85decode(encoded))
if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
    raise SystemExit('decoded Python source SHA-256 mismatch')

repair_script = Path('scripts/repair_comparisons_v331.py')
repair_tests = Path('tests/test_comparisons_v331.py')
if not repair_script.is_file() or not repair_tests.is_file():
    raise SystemExit('comparison repair v331 sources are missing')
py_compile.compile(str(repair_script), doraise=True)
py_compile.compile(str(repair_tests), doraise=True)
subprocess.run(
    [sys.executable, '-m', 'unittest', '-v', str(repair_tests)],
    check=True,
)

hook = b'''\n\n# Comparison quality publisher v331: replaces the legacy duplicated/thin pages\n# after the verified v9 expander finishes, while preserving all 100 public URLs.\nif __name__ == "__main__":\n    import runpy as _comparison_runpy\n    from pathlib import Path as _ComparisonPath\n    _comparison_runpy.run_path(\n        str(_ComparisonPath(__file__).resolve().parent / "scripts" / "repair_comparisons_v331.py"),\n        run_name="__main__",\n    )\n'''
augmented_source = source + hook
Path('expand_site_v9.py').write_bytes(augmented_source)
print(
    'v9 expander verified:',
    len(source),
    'bytes; comparisons v331 hook:',
    len(hook),
    'bytes',
)
