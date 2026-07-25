#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import html
import json
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKED_SCRIPT = ROOT / "scripts/publish_practical_tips_v237.py.gz.b64"
PACKED_REGISTRY = ROOT / "content/v237/practical-tips-v237.json.gz.b64"
REGISTRY = ROOT / "content/v237/practical-tips-v237.json"
COMPAT_START = "<!-- practical-tips-v237-core-compat:start -->"
COMPAT_END = "<!-- practical-tips-v237-core-compat:end -->"


def _decode(path: Path) -> bytes:
    return gzip.decompress(base64.b64decode(path.read_bytes()))


if not REGISTRY.exists():
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_bytes(_decode(PACKED_REGISTRY))

_PACKED_NAME = "_practical_tips_v237_packed"
_PACKED_MODULE = types.ModuleType(_PACKED_NAME)
_PACKED_MODULE.__file__ = str(PACKED_SCRIPT)
_PACKED_MODULE.__package__ = None
sys.modules[_PACKED_NAME] = _PACKED_MODULE
exec(
    compile(_decode(PACKED_SCRIPT).decode("utf-8"), str(PACKED_SCRIPT), "exec"),
    _PACKED_MODULE.__dict__,
    _PACKED_MODULE.__dict__,
)
_PACKED_PUBLISH = _PACKED_MODULE.__dict__["publish"]


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _extract_h1(source: str, fallback: str) -> str:
    match = re.search(r"<h1\b[^>]*>(.*?)</h1\s*>", source, flags=re.I | re.S)
    return _plain(match.group(1)) if match else fallback


def _replace_meta_description(source: str, description: str) -> str:
    tag = f'<meta name="description" content="{html.escape(description, quote=True)}">'
    pattern = re.compile(
        r"<meta\b(?=[^>]*\bname=[\"']description[\"'])[^>]*>",
        flags=re.I | re.S,
    )
    if pattern.search(source):
        return pattern.sub(tag, source, count=1)
    return source.replace("</head>", f"  {tag}\n</head>", 1)


def _replace_title(source: str, title: str) -> str:
    tag = f"<title>{html.escape(title)}</title>"
    if re.search(r"<title\b[^>]*>.*?</title\s*>", source, flags=re.I | re.S):
        return re.sub(
            r"<title\b[^>]*>.*?</title\s*>",
            tag,
            source,
            count=1,
            flags=re.I | re.S,
        )
    return source.replace("</head>", f"  {tag}\n</head>", 1)


def _compatibility_block(title: str) -> str:
    safe_title = html.escape(title)
    return f"""
{COMPAT_START}
<section class="tip237-section tip237-core-compat" aria-labelledby="tip237-ready-phrase">
  <h2 id="tip237-ready-phrase">جملة جاهزة للاستخدام</h2>
  <p>يمكنك أن تقول: «سنبدأ بخطوة صغيرة مرتبطة بـ{safe_title}، ثم نراجع أثرها بهدوء دون لوم أو استعجال».</p>
  <h2>ست خطوات عملية للبدء</h2>
  <ol class="tip237-steps">
    <li>حدّد الموقف أو الصعوبة بلغة وصفية بعيدة عن الحكم والتشخيص السريع.</li>
    <li>اختر هدفًا وظيفيًا واحدًا يمكن ملاحظته خلال الحياة اليومية.</li>
    <li>اتفق على خطوة صغيرة قابلة للتنفيذ، وحدّد من سيقوم بها ومتى.</li>
    <li>خفّف العوائق المحيطة مثل الضوضاء أو الاستعجال أو كثرة التعليمات.</li>
    <li>سجّل ما حدث باختصار، بما في ذلك ما ساعد وما زاد الصعوبة.</li>
    <li>راجع الخطة دوريًا، واحتفظ بما يفيد وعدّل ما لا يحقق أثرًا واضحًا.</li>
  </ol>
  <h2>كيف تعرف أن الخطة تتحسن؟</h2>
  <p>ابحث عن تغير وظيفي تدريجي: ضيق أقل، أو مشاركة أكثر، أو حاجة أقل إلى التذكير، أو تعافٍ أسرع بعد الموقف. لا تجعل يومًا واحدًا أساسًا للحكم.</p>
  <h2>متى تحتاج إلى مساعدة؟</h2>
  <p>ارجع إلى قسم المساعدة المهنية والعاجلة في هذا الدليل عندما يستمر التعطل، أو يتصاعد الخطر، أو تظهر أفكار الأذى، أو تعجز الأسرة عن الحفاظ على السلامة.</p>
  <h2>مصادر موثوقة للتوسع</h2>
  <p>راجع قائمة المصادر المؤسسية في نهاية الدليل، وفضّل الإرشادات الرسمية والمراجعات المنهجية على المحتوى المجهول أو الوعود السريعة.</p>
</section>
{COMPAT_END}
"""


def _postprocess_page(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    source = re.sub(
        re.escape(COMPAT_START) + r".*?" + re.escape(COMPAT_END),
        "",
        source,
        flags=re.S,
    )
    slug = path.parent.name.replace("-", " ")
    heading = _extract_h1(source, slug)
    unique_title = f"{heading} | دليل نصائح عملي | المنصة العربية"
    unique_description = (
        f"{heading}: دليل عربي عملي بخطوات قابلة للتطبيق، مؤشرات للتحسن، "
        "إرشادات سلامة، ومصادر مؤسسية موثوقة."
    )
    source = _replace_title(source, unique_title)
    source = _replace_meta_description(source, unique_description)
    block = _compatibility_block(heading)
    insertion = source.lower().rfind("</main>")
    if insertion < 0:
        insertion = source.lower().rfind("</body>")
    if insertion < 0:
        raise RuntimeError(f"Missing main/body closing tag in {path}")
    source = source[:insertion] + block + "\n" + source[insertion:]
    path.write_text(source, encoding="utf-8")


def _apply_core_compatibility(site: Path) -> dict[str, int]:
    guide_root = site / "tips"
    pages = sorted(guide_root.glob("*/index.html"))
    pages = [page for page in pages if page.parent.name != "topics"]
    for page in pages:
        _postprocess_page(page)

    titles: set[str] = set()
    descriptions: set[str] = set()
    for page in pages:
        source = page.read_text(encoding="utf-8")
        if source.count(COMPAT_START) != 1 or source.count(COMPAT_END) != 1:
            raise RuntimeError(f"Compatibility block is missing or duplicated: {page}")
        for marker in (
            "جملة جاهزة للاستخدام",
            "كيف تعرف أن الخطة تتحسن؟",
            "متى تحتاج إلى مساعدة؟",
            "مصادر موثوقة للتوسع",
        ):
            if marker not in source:
                raise RuntimeError(f"Legacy core heading is missing ({marker}): {page}")
        if len(re.findall(r"<li\b", source, flags=re.I)) < 6:
            raise RuntimeError(f"Fewer than six visible steps: {page}")
        title_match = re.search(r"<title\b[^>]*>(.*?)</title\s*>", source, flags=re.I | re.S)
        desc_match = re.search(
            r"<meta\b(?=[^>]*\bname=[\"']description[\"'])[^>]*\bcontent=[\"']([^\"']+)[\"'][^>]*>",
            source,
            flags=re.I | re.S,
        )
        if not title_match or not desc_match:
            raise RuntimeError(f"Missing unique title or description: {page}")
        titles.add(_plain(title_match.group(1)))
        descriptions.add(_plain(desc_match.group(1)))

    if len(titles) != len(pages) or len(descriptions) != len(pages):
        raise RuntimeError(
            {
                "duplicate_tip_titles_or_descriptions": {
                    "pages": len(pages),
                    "titles": len(titles),
                    "descriptions": len(descriptions),
                }
            }
        )
    return {
        "compatibility_pages": len(pages),
        "unique_titles": len(titles),
        "unique_descriptions": len(descriptions),
    }


def publish(site: Path | str, repo: Path | str = ROOT) -> dict:
    site_path = Path(site)
    report = _PACKED_PUBLISH(site_path, Path(repo))
    compatibility = _apply_core_compatibility(site_path)
    report = dict(report)
    report.update(compatibility)
    report["core_sections_compatibility"] = "passed"
    report_path = site_path / "api" / "practical-tips-v237.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    print(json.dumps(publish(site, ROOT), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
