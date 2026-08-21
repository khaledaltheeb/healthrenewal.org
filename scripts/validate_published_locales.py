from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "published-locales.json"
HREFLANG_RE = re.compile(r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+href="([^"]+)"', re.I)


def main() -> None:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    origin = data["canonical_origin"].rstrip("/")
    locales = data["locales"]
    expected = {entry["code"]: entry for entry in locales if entry["status"] == "published"}
    errors: list[str] = []

    for code, entry in expected.items():
        artifact = ROOT / entry["artifact"]
        if not artifact.is_file():
            errors.append(f"{code}: missing artifact {entry['artifact']}")
            continue
        html = artifact.read_text(encoding="utf-8")
        if f'<html lang="{code}" dir="{entry["direction"]}">' not in html:
            errors.append(f"{code}: lang/dir does not match registry")
        canonical = origin + (entry["path"] if entry["path"] != "/" else "/")
        if f'<link rel="canonical" href="{canonical}">' not in html:
            errors.append(f"{code}: missing self canonical {canonical}")
        alternates = dict(HREFLANG_RE.findall(html))
        for other_code, other in expected.items():
            target = origin + (other["path"] if other["path"] != "/" else "/")
            if alternates.get(other_code) != target:
                errors.append(f"{code}: hreflang {other_code} != {target}")
        if alternates.get("x-default") != origin + "/":
            errors.append(f"{code}: x-default must point to Arabic root")

    home = (ROOT / "index.html").read_text(encoding="utf-8")
    for code, entry in expected.items():
        if code == data["default_locale"]:
            continue
        if f'href="{entry["path"]}"' not in home and f'href="{origin}{entry["path"]}"' not in home:
            errors.append(f"homepage: published locale {code} is not visibly linked")

    legacy = [entry for entry in locales if entry["status"] != "published"]
    for entry in legacy:
        if f'href="{entry["path"]}"' in home:
            errors.append(f"homepage: non-published locale {entry['code']} is visible")

    if errors:
        raise SystemExit("Published locale contract failed:\n- " + "\n- ".join(errors))
    print(json.dumps({"status": "passed", "published_locales": sorted(expected), "canonical_origin": origin}, ensure_ascii=False))


if __name__ == "__main__":
    main()
