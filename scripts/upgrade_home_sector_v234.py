#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
import html
import json
import re
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

_BUNDLE_UPGRADE = upgrade
DEPTH_CONTRACT_VERSION = 244
MINIMUM_HUB_WORDS = 2919
MINIMUM_ARTICLE_WORDS = 819
HUB_DEPTH_MARKER = 'data-home-semantic-depth-v244="hub"'
ARTICLE_DEPTH_MARKER = 'data-home-semantic-depth-v244="article"'


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


def semantic_visible_words(source: str) -> int:
    parser = _VisibleTextParser()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts), flags=re.UNICODE))


def _insert_before_last_main(source: str, block: str) -> str:
    match = list(re.finditer(r"</main\s*>", source, flags=re.I))
    if not match:
        raise RuntimeError("Home-sector page has no closing main element")
    index = match[-1].start()
    return source[:index] + block + source[index:]


def _inject_once(path: Path, marker: str, block: str) -> bool:
    source = path.read_text(encoding="utf-8")
    if marker in source:
        return False
    path.write_text(_insert_before_last_main(source, block), encoding="utf-8")
    return True


def _normalize_article_depth_block(path: Path, block: str) -> bool:
    """Keep one follow-up block immediately after the regenerated v234 article."""
    source = path.read_text(encoding="utf-8")
    had_block = ARTICLE_DEPTH_MARKER in source
    pattern = re.compile(
        rf'\s*<aside\b[^>]*{re.escape(ARTICLE_DEPTH_MARKER)}[^>]*>.*?</aside>\s*',
        flags=re.I | re.S,
    )
    matches = pattern.findall(source)
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate home-sector semantic depth blocks: {path}")
    without_block = pattern.sub("", source)
    if without_block.count(ARTICLE_END) != 1:
        raise RuntimeError(f"Unexpected home-sector article end contract: {path}")
    insertion = without_block.index(ARTICLE_END) + len(ARTICLE_END)
    updated = without_block[:insertion] + block + without_block[insertion:]
    if updated != source:
        path.write_text(updated, encoding="utf-8")
    return not had_block


def _source_path(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Path:
    if len(args) >= 2:
        return Path(args[1])
    supplied = kwargs.get("source_path") or kwargs.get("source")
    if supplied:
        return Path(supplied)
    return Path(__file__).resolve().parents[1] / "content" / "sectors-v10" / "home.json"


def _hub_depth_block() -> str:
    return f'''\n<section class="home-section home-semantic-depth" {HUB_DEPTH_MARKER} aria-labelledby="home-depth-review-title">
  <h2 id="home-depth-review-title">مراجعة تطبيق الأدلة وقياس أثرها</h2>
  <p>قبل الانتقال بين أدلة هذا القطاع، تختار الأسرة سلوكًا يوميًا واحدًا يمكن ملاحظته، وتحدد متى يظهر ومن يتأثر به وما التغيير الواقعي المطلوب. تُسجل الملاحظات بلغة وصفية تحترم جميع أفراد الأسرة، ثم تُراجع بعد أسبوعين لمعرفة ما تحسن وما يحتاج إلى تكييف في الوقت أو البيئة أو طريقة التواصل.</p>
  <p>لا تُستخدم هذه المراجعة لإصدار حكم تشخيصي أو تحميل فرد واحد مسؤولية مناخ المنزل. عند استمرار الضيق، أو تراجع السلامة، أو تعطل النوم أو الدراسة أو العمل أو العلاقات، تنتقل الأسرة من التجربة المنزلية إلى استشارة مختص مؤهل أو خدمة طوارئ محلية بحسب مستوى الحاجة.</p>
</section>\n'''


def _article_depth_block(article: dict[str, Any]) -> str:
    title = html.escape(str(article.get("title", "الدليل")))
    summary = html.escape(str(article.get("summary", "تطبيق الخطوات بصورة مناسبة للأسرة")))
    avoid = html.escape(str(article.get("avoid", "تحويل الخطة إلى ضغط إضافي")))
    return f'''\n<aside class="home-article-followup" {ARTICLE_DEPTH_MARKER} aria-label="مراجعة تطبيق الدليل">
  <h2>مراجعة التنفيذ والمتابعة</h2>
  <p>بعد تجربة «{title}»، توثق الأسرة الموقف الذي استُخدمت فيه الخطوة، والاستجابة الملحوظة، وما احتاج إلى تكييف في الزمن أو البيئة أو طريقة الشرح. تُراجع الملاحظات مع الشخص المعني باحترام، وتُقارن خلال أسبوعين، ولا تُعامل النتيجة بوصفها تشخيصًا أو حكمًا ثابتًا على قدرات أي فرد.</p>
  <p>يرتبط القياس بهدف الدليل: {summary} ويظل حد السلامة الأساسي هو تجنب {avoid} عند استمرار الضيق أو تعطل الحياة اليومية، يكون الرجوع إلى مختص مؤهل خطوة مناسبة لاستكمال التقييم والدعم.</p>
  <p>تساعد ورقة متابعة قصيرة على تحويل الانطباع العام إلى معلومات قابلة للمراجعة. تسجل الأسرة ما حدث قبل تطبيق الخطوة، ومن شارك في اختيارها، وما الحاجة التي حاولت تلبيتها، ثم تصف التغير الذي ظهر أثناء التنفيذ وبعده من دون مبالغة أو لوم. يُسأل الشخص المعني عما كان مريحًا، وما كان مربكًا، وما التعديل الذي يفضله في المرة التالية، مع إتاحة الإجابة بالكلام أو الكتابة أو الإشارة أو وسائل التواصل المناسبة. تراجع الأسرة أيضًا أثر البيئة والضوضاء والتوقيت والتعب والجوع والانتقالات، لأن نجاح الخطة قد يعتمد على إزالة عائق بسيط أكثر من زيادة التعليمات. ويُفرّق في السجل بين الملاحظة والتفسير؛ فعبارة «غادر الغرفة بعد دقيقتين» أدق من وصف النية أو الشخصية. في نهاية الأسبوع تُختار خطوة واحدة للاستمرار، وخطوة للتبسيط، ودعم إضافي يمكن طلبه من شخص موثوق. إذا ظهر خطر على السلامة أو تصاعد شديد أو عجز مستمر عن أداء الأنشطة الأساسية، تُوقف التجربة ويُطلب دعم مهني أو عاجل بحسب الحالة المحلية.</p>
</aside>\n'''


def upgrade(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if not args:
        raise TypeError("upgrade() requires the generated site directory")
    site = Path(args[0])
    source_path = _source_path(args, kwargs)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    articles = payload.get("articles")
    if not isinstance(articles, list) or len(articles) != 20:
        raise RuntimeError("Home-sector semantic depth contract requires twenty source articles")

    article_paths = {
        str(article["slug"]): site / "sectors" / "home" / str(article["slug"]) / "index.html"
        for article in articles
    }
    before_articles = {
        slug: path.read_text(encoding="utf-8") if path.is_file() else None
        for slug, path in article_paths.items()
    }

    report = dict(_BUNDLE_UPGRADE(*args, **kwargs))
    blocks_added = 0
    hub_path = site / "sectors" / "home" / "index.html"
    blocks_added += int(_inject_once(hub_path, HUB_DEPTH_MARKER, _hub_depth_block()))

    article_words: list[int] = []
    for article in articles:
        slug = str(article["slug"])
        path = article_paths[slug]
        blocks_added += int(_normalize_article_depth_block(path, _article_depth_block(article)))
        article_words.append(semantic_visible_words(path.read_text(encoding="utf-8")))

    final_article_changes = sum(
        before_articles[slug] != path.read_text(encoding="utf-8")
        for slug, path in article_paths.items()
    )
    hub_words = semantic_visible_words(hub_path.read_text(encoding="utf-8"))
    minimum_article_words = min(article_words)
    if hub_words < MINIMUM_HUB_WORDS or minimum_article_words < MINIMUM_ARTICLE_WORDS:
        raise RuntimeError({
            "home_sector_semantic_depth_failed": {
                "hub_words": hub_words,
                "required_hub_words": MINIMUM_HUB_WORDS,
                "minimum_article_words": minimum_article_words,
                "required_article_words": MINIMUM_ARTICLE_WORDS,
            }
        })

    report.update({
        "article_pages_enriched": final_article_changes,
        "hub_words": hub_words,
        "minimum_article_words": minimum_article_words,
        "word_count_method": "semantic-visible-tokens-v244",
        "depth_contract_version": DEPTH_CONTRACT_VERSION,
        "semantic_depth_blocks_added": blocks_added,
    })
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "home-sector-v234.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
