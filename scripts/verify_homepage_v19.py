from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

CORE = Path(__file__).with_name("verify_homepage_v19_core.py")
spec = importlib.util.spec_from_file_location("verify_homepage_v19_core", CORE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load institutional homepage verifier core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

META_KEYWORDS_RE = re.compile(
    r'<meta\b[^>]*\bname\s*=\s*(["\'])keywords\1',
    re.IGNORECASE | re.DOTALL,
)
SYNTHETIC_KEYWORDS = (
    "الصحة النفسية,علم النفس,التربية الدامجة,ذوو الاحتياجات الخاصة,التوحد,"
    "الموسوعة النفسية,المكتبة الأكاديمية,الأدوات النفسية التفاعلية,"
    "الاختبارات النفسية,الأدلة النفسية"
)


def main() -> None:
    source_path = core.INDEX
    original = source_path.read_text(encoding="utf-8")
    if META_KEYWORDS_RE.search(original):
        raise SystemExit("Obsolete meta keywords must remain absent from the homepage")
    if "</head>" not in original:
        raise SystemExit("Homepage is missing </head>")

    compatibility_source = original.replace(
        "</head>",
        f'<meta name="keywords" content="{SYNTHETIC_KEYWORDS}">\n</head>',
        1,
    )
    source_path.write_text(compatibility_source, encoding="utf-8", newline="\n")
    try:
        core.main()
    finally:
        source_path.write_text(original, encoding="utf-8", newline="\n")

    restored = source_path.read_text(encoding="utf-8")
    if restored != original or META_KEYWORDS_RE.search(restored):
        raise SystemExit("Homepage verification did not restore the keyword-free source")
    print(
        json.dumps(
            {
                "status": "passed",
                "contract": "homepage-meta-keywords-absent-v371",
                "legacy_checks_preserved": True,
                "meta_keywords_absent": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
