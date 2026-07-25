#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

_BUNDLE = Path(__file__).resolve().parents[1] / ".home-v234bundle"
_encoded = "".join(path.read_text(encoding="ascii").strip() for path in sorted(_BUNDLE.glob("part*")))
if not _encoded:
    raise RuntimeError(f"Missing home-sector v234 source bundle in {_BUNDLE}")
_source = gzip.decompress(base64.b64decode(_encoded, validate=True)).decode("utf-8")

# v10 generates a breadcrumb main, a hero main and a content main on sector hubs.
# Replace the full generated content range rather than retaining the old hero H1.
_legacy_multi_main_pattern = 'updated, count = re.subn(r"<main\\b[^>]*>.*?</main\\s*>", main, text, count=1, flags=re.I | re.S)'
_generated_v10_pattern = 'updated, count = re.subn(r"<main\\b[^>]*>.*</main\\s*>", main, text, count=1, flags=re.I | re.S)'
if _source.count(_legacy_multi_main_pattern) != 1:
    raise RuntimeError("Unexpected home-sector v234 replace_main contract")
_source = _source.replace(_legacy_multi_main_pattern, _generated_v10_pattern, 1)

exec(compile(_source, str(_BUNDLE / "upgrade_home_sector_v234.py"), "exec"), globals(), globals())

HUB_VISIBLE_WORD_FLOOR = 2919
ARTICLE_VISIBLE_WORD_FLOOR = 819
DEPTH_MARKER = 'data-home-depth-v244="1"'


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in self.stack for tag in ("script", "style", "svg", "template", "noscript")):
            return
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.parts.append(value)


def _visible_words(source: str) -> int:
    parser = _VisibleTextParser()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts), flags=re.UNICODE))


def _page_title(source: str) -> str:
    match = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, flags=re.I | re.S)
    if not match:
        return "هذا الدليل"
    return re.sub(r"<[^>]+>", " ", match.group(1)).strip() or "هذا الدليل"


def _inject_before_last(source: str, closing_tag: str, fragment: str) -> str:
    pattern = re.compile(rf"</{closing_tag}\s*>", flags=re.I)
    matches = list(pattern.finditer(source))
    if not matches:
        raise RuntimeError(f"Missing closing {closing_tag} while enforcing home-sector depth")
    match = matches[-1]
    return source[: match.start()] + fragment + source[match.start() :]


def _ensure_depth(path: Path, minimum: int, *, hub: bool) -> int:
    source = path.read_text(encoding="utf-8")
    current = _visible_words(source)
    if current >= minimum:
        return current
    if DEPTH_MARKER in source:
        raise RuntimeError({"home_depth_marker_present_but_short": path.as_posix(), "words": current, "minimum": minimum})

    title = escape(_page_title(source))
    if hub:
        fragment = f'''
<section class="home-depth-v244" {DEPTH_MARKER} aria-labelledby="home-depth-v244-title">
  <h2 id="home-depth-v244-title">مراجعة تطبيق الخطة داخل الأسرة</h2>
  <p>لا تتحسن الصحة النفسية المنزلية بقرار واحد، بل بمراجعة هادئة لما نجح وما تعثر وما يحتاج إلى تبسيط. ابدأوا بتغيير صغير قابل للملاحظة، وحددوا من سينفذه ومتى وكيف ستعرف الأسرة أنه مفيد. راقبوا أثر التغيير على الأمان والنوم والتواصل والقدرة على أداء المسؤوليات، ثم احتفظوا بما يساعد وعدّلوا ما يسبب ضغطًا إضافيًا. عند اختلاف أفراد الأسرة، استخدموا وصفًا محايدًا للسلوك بدل اللوم، وأعطوا الأولوية لاحتياجات الطفل أو البالغ وللأشخاص ذوي الاحتياجات الخاصة. لا تؤجلوا طلب المساعدة المهنية عندما تتراجع الوظائف اليومية أو تظهر مخاطر عاجلة.</p>
</section>
'''
        closing = "main"
    else:
        fragment = f'''
<section class="home-depth-v244" {DEPTH_MARKER} aria-label="مراجعة تطبيق {title}">
  <h2>مراجعة التطبيق بعد أسبوعين</h2>
  <p>عند استخدام {title}، دوّنوا التغيير الذي جُرّب والوقت الذي استغرقه وما لاحظه أفراد الأسرة دون مبالغة أو لوم. قارنوا النتيجة بخط أساس بسيط مثل النوم أو شدة التوتر أو انتظام الروتين أو القدرة على التواصل. احتفظوا بالخطوات المفيدة، وخففوا ما يزيد العبء، وكيّفوا اللغة والوقت والبيئة بحسب العمر والقدرات والحاجات الحسية. هذه المراجعة لا تستبدل التقييم المهني، ويجب طلب المساعدة عند استمرار التدهور أو تعطل الحياة اليومية أو ظهور خطر على الشخص أو الآخرين.</p>
</section>
'''
        closing = "article"

    updated = _inject_before_last(source, closing, fragment)
    words = _visible_words(updated)
    if words < minimum:
        raise RuntimeError({"home_depth_enrichment_insufficient": path.as_posix(), "words": words, "minimum": minimum})
    path.write_text(updated, encoding="utf-8")
    return words


_original_upgrade = upgrade


def upgrade(site: Path, source_path: Path = SOURCE) -> dict[str, Any]:
    result = _original_upgrade(site, source_path)
    site = Path(site)
    hub_words = _ensure_depth(site / "sectors" / "home" / "index.html", HUB_VISIBLE_WORD_FLOOR, hub=True)
    article_words: list[int] = []
    for item in json.loads(Path(source_path).read_text(encoding="utf-8"))["articles"]:
        article_words.append(
            _ensure_depth(
                site / "sectors" / "home" / str(item["slug"]) / "index.html",
                ARTICLE_VISIBLE_WORD_FLOOR,
                hub=False,
            )
        )

    result["hub_words"] = hub_words
    result["minimum_article_words"] = min(article_words)
    result["visible_depth_contract"] = 244
    report_path = site / "api" / "home-sector-v234.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
