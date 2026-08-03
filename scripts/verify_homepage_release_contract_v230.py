from __future__ import annotations

"""تحقق حتمي من أن الصفحة الرئيسية تمثل الإصدار المؤسسي الحالي.

يمنع هذا العقد نشر واجهة قديمة حتى لو كانت بعض الصفحات الداخلية الحديثة
موجودة في الحزمة. لا يقيّم جودة المحتوى الطبي، بل يتحقق من الهوية وبوابات
الاكتشاف والمؤشرات الصريحة للرجوع إلى نسخة سابقة.
"""

import argparse
import json
import re
from pathlib import Path

VERSION = 230
INSTITUTIONAL_NAME = "منصة روافد"
REQUIRED_HREFS = (
    "sections/",
    "partners/",
    "developers/",
    "magazine/",
    "trust/",
    "comparisons/",
    "library/",
    "daily-tools/",
    "learning-paths/",
)
REQUIRED_MARKERS = (
    INSTITUTIONAL_NAME,
    "2,000+",
    "93",
    '"@type":"Organization"',
)
FORBIDDEN_MARKERS = (
    "88 مقياسًا وأداة وقدرة معرفية",
    "© مصطلحات علم النفس — منصة عربية تثقيفية منظمة.",
    "مركز أساسي للأشخاص ذوي الإعاقة",
    "ذوو الإعاقة",
    "ذوي الإعاقة",
    "المعاقين",
    "معاقين",
)


def inspect_html(html: str, source: str = "index.html") -> dict[str, object]:
    errors: list[str] = []
    title_match = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
    if INSTITUTIONAL_NAME not in title:
        errors.append("institutional title is missing")

    missing_markers = [marker for marker in REQUIRED_MARKERS if marker not in html]
    if missing_markers:
        errors.append(f"missing release markers: {missing_markers}")

    missing_hrefs = [href for href in REQUIRED_HREFS if f'href="{href}"' not in html]
    if missing_hrefs:
        errors.append(f"missing homepage gateways: {missing_hrefs}")

    forbidden_found = [marker for marker in FORBIDDEN_MARKERS if marker in html]
    if forbidden_found:
        errors.append(f"legacy or prohibited homepage markers found: {forbidden_found}")

    organization_pattern = re.compile(
        r'"@type":"Organization"[^{}]*"name":"' + re.escape(INSTITUTIONAL_NAME) + r'"'
    )
    if not organization_pattern.search(html):
        errors.append("institutional Organization structured data is missing")

    if html.count('<link rel="canonical"') != 1:
        errors.append("homepage must contain exactly one canonical link")
    if html.count('<meta name="description"') != 1:
        errors.append("homepage must contain exactly one meta description")
    if '<meta name="robots" content="index,follow' not in html:
        errors.append("indexable robots contract is missing")

    return {
        "version": VERSION,
        "source": source,
        "status": "passed" if not errors else "failed",
        "title": title,
        "required_gateways": list(REQUIRED_HREFS),
        "missing_gateways": missing_hrefs,
        "forbidden_markers_found": forbidden_found,
        "errors": errors,
    }


def verify(path: Path, report_path: Path | None = None) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"Missing homepage: {path}")
    report = inspect_html(path.read_text(encoding="utf-8"), str(path))
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if report["status"] != "passed":
        raise SystemExit("Homepage release contract v230 failed:\n" + "\n".join(report["errors"]))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("homepage", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.homepage, args.report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
