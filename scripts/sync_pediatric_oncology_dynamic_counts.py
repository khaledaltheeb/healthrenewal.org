#!/usr/bin/env python3
"""Synchronize pediatric-oncology hub counters with the materialization report.

The evidence materializer owns the article/hub bodies. This script owns only the
count-bearing title/description/H1 fragments and the legacy compatibility page.
It is intentionally deterministic so repeated runs with unchanged counts are
no-ops.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

REPORT = Path("api/pediatric-oncology-materialization-v1.json")
LEGACY_ALIAS = Path("sections/pediatric-cancer-latest-100-theses/index.html")
BASE_URL = "https://healthrenewal.org"
START_MARKER = "<!-- rawafid:pediatric-oncology-dynamic-counts:v1 -->"
END_MARKER = "<!-- /rawafid:pediatric-oncology-dynamic-counts:v1 -->"
OWNER_MARKER = "<!-- rawafid:pediatric-oncology-materializer:v1 -->"
BLOCK_RE = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.S)
TITLE_RE = re.compile(r"<title>.*?</title>", re.S)
DESCRIPTION_RE = re.compile(r'<meta name="description" content="[^"]*">', re.S)
H1_RE = re.compile(r"<h1>.*?</h1>", re.S)


@dataclass(frozen=True)
class Hub:
    path: Path
    count_key: str
    base_title: str
    unit: str
    description_prefix: str


HUBS = (
    Hub(
        Path("magazine/pediatric-oncology/index.html"),
        "records",
        "أبحاث سرطان الأطفال",
        "مادة موثقة",
        "مركز روافد للقراءات العلمية الحديثة والرسائل الجامعية المرتبطة بأورام الأطفال، مع المصادر الأصلية وحدود الدليل.",
    ),
    Hub(
        Path("magazine/pediatric-oncology/studies/index.html"),
        "studies",
        "أحدث دراسات سرطان الأطفال",
        "دراسة موثقة",
        "قراءات عربية نقدية للدراسات المحكمة الحديثة في أورام الأطفال، مع التصميم والعينة والنتائج والقيود والمصدر الأصلي.",
    ),
    Hub(
        Path("magazine/pediatric-oncology/theses/index.html"),
        "theses",
        "الرسائل الجامعية في سرطان الأطفال",
        "رسالة جامعية موثقة",
        "ملخصات عربية موثقة للرسائل والأطروحات الجامعية الحديثة ذات الصلة بأورام الأطفال، مع السجل الجامعي الأصلي وحدود الاستدلال.",
    ),
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_report(root: Path) -> dict[str, int]:
    path = root / REPORT
    if not path.is_file():
        raise RuntimeError(f"Missing materialization report: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("status") != "passed":
        raise RuntimeError("Pediatric-oncology materialization report is not passed")
    values: dict[str, int] = {}
    for key in ("records", "studies", "theses"):
        value = raw.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RuntimeError(f"Invalid report count for {key}: {value!r}")
        values[key] = value
    if values["records"] != values["studies"] + values["theses"]:
        raise RuntimeError(
            "Count contract mismatch: records must equal studies + theses "
            f"({values['records']} != {values['studies']} + {values['theses']})"
        )
    return values


def replace_once(pattern: re.Pattern[str], replacement: str, text: str, label: str) -> str:
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label}; found {count}")
    return updated


def dynamic_title(hub: Hub, count: int) -> str:
    return f"{hub.base_title} — العدد الحالي: {count}"


def dynamic_description(hub: Hub, count: int) -> str:
    return f"{hub.description_prefix} العدد الحالي: {count} {hub.unit}."


def count_block(hub: Hub, count: int) -> str:
    return (
        f'{START_MARKER}<p class="meta" data-current-count="{count}" '
        f'data-count-source="api/pediatric-oncology-materialization-v1.json">'
        f'العدد الحالي المنشور: <strong>{count}</strong> {esc(hub.unit)}. '
        "يتغير هذا العداد تلقائيًا مع كل تحديث ناجح للمصدر.</p>"
        f"{END_MARKER}"
    )


def render_hub(text: str, hub: Hub, count: int) -> str:
    if OWNER_MARKER not in text:
        raise RuntimeError(f"Refusing to patch non-materializer hub: {hub.path}")

    title = esc(dynamic_title(hub, count))
    description = esc(dynamic_description(hub, count))
    updated = replace_once(TITLE_RE, f"<title>{title} | منصة روافد</title>", text, "title")
    updated = replace_once(
        DESCRIPTION_RE,
        f'<meta name="description" content="{description}">',
        updated,
        "meta description",
    )
    updated = replace_once(H1_RE, f"<h1>{title}</h1>", updated, "h1")

    block = count_block(hub, count)
    if BLOCK_RE.search(updated):
        updated = BLOCK_RE.sub(block, updated, count=1)
    else:
        h1_match = H1_RE.search(updated)
        if not h1_match:
            raise RuntimeError(f"Cannot insert dynamic count block in {hub.path}")
        updated = updated[: h1_match.end()] + block + updated[h1_match.end() :]
    return updated


def legacy_alias_html(theses: int) -> str:
    canonical_path = "/magazine/pediatric-oncology/theses/"
    canonical = BASE_URL + canonical_path
    title = f"الرسائل الجامعية في سرطان الأطفال — العدد الحالي: {theses}"
    description = (
        "هذا هو رابط التوافق القديم الذي كان يحمل رقم 100 في المسار. "
        f"العدد الفعلي الحالي هو {theses} ويُقرأ آليًا من سجل النشر."
    )
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)} | منصة روافد</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{esc(canonical)}">
<style>
body{{font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#173f45;background:#f7fbfa;margin:0}}
main{{width:min(820px,92%);margin:auto;padding:48px 0 72px}}
article{{background:#fff;border:1px solid #cfe7e3;border-radius:20px;padding:clamp(20px,4vw,32px)}}
a{{color:#075f5b}} .meta{{color:#527174}}
</style>
</head>
<body>
{START_MARKER}
<main><article>
<p class="meta">مسار توافق قديم</p>
<h1>{esc(title)}</h1>
<p>الرقم <b>100</b> جزء من عنوان URL القديم فقط، ولا يُستخدم بعد الآن كعداد للمحتوى.</p>
<p data-current-count="{theses}" data-count-source="api/pediatric-oncology-materialization-v1.json">العدد الحالي المنشور: <strong>{theses}</strong>.</p>
<p><a href="{canonical_path}">فتح الفهرس الحالي للرسائل الجامعية في سرطان الأطفال</a></p>
</article></main>
{END_MARKER}
</body>
</html>
'''


def desired_outputs(root: Path, counts: dict[str, int]) -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    for hub in HUBS:
        path = root / hub.path
        if not path.is_file():
            raise RuntimeError(f"Missing pediatric-oncology hub: {path}")
        current = path.read_text(encoding="utf-8")
        outputs[path] = render_hub(current, hub, counts[hub.count_key])
    outputs[root / LEGACY_ALIAS] = legacy_alias_html(counts["theses"])
    return outputs


def synchronize(root: Path, *, check: bool) -> list[str]:
    counts = load_report(root)
    outputs = desired_outputs(root, counts)
    changed: list[str] = []
    for path, desired in outputs.items():
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current == desired:
            continue
        changed.append(path.relative_to(root).as_posix())
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(desired, encoding="utf-8", newline="\n")
    if check and changed:
        raise RuntimeError("Dynamic pediatric-oncology counts are stale: " + ", ".join(changed))
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--check", action="store_true", help="Fail if any generated count is stale")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Repository root does not exist: {root}")
    changed = synchronize(root, check=args.check)
    counts = load_report(root)
    print(json.dumps({"status": "passed", "counts": counts, "changed": changed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
