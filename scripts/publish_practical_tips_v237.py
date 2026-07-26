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
TOPIC_START = "<!-- practical-tips-v237-topic-depth:start -->"
TOPIC_END = "<!-- practical-tips-v237-topic-depth:end -->"
SEARCH_START = "<!-- practical-tips-v248-search:start -->"
SEARCH_END = "<!-- practical-tips-v248-search:end -->"
TOPIC_MINIMUM_CHARACTERS = 1800


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


def _topic_depth_block(title: str) -> str:
    safe_title = html.escape(title)
    return f"""
{TOPIC_START}
<section class="tip237-section tip237-topic-depth" aria-labelledby="tip237-topic-method">
  <h2 id="tip237-topic-method">كيف تستخدم مسار {safe_title} بطريقة منهجية؟</h2>
  <p>هذا المسار ليس قائمة تعليمات تُنفّذ دفعة واحدة، بل خريطة عملية تساعدك على الانتقال من وصف المشكلة إلى تجربة تعديل صغير ثم مراجعة أثره. ابدأ بالدليل الأقرب إلى الموقف الحالي، واقرأ حدود استخدامه قبل اختيار أي خطوة. ركّز على الوظيفة اليومية: النوم، المشاركة، التواصل، الدراسة، العمل، الرعاية الذاتية أو جودة العلاقة، بدل الاكتفاء بوصف شعور عام أو البحث عن تسمية سريعة.</p>
  <p>دوّن قبل البدء مثالًا واقعيًا واحدًا: ماذا حدث، ومتى، ومن كان حاضرًا، وما العوامل التي سبقت الموقف، وما الذي خفّف الصعوبة أو زادها. هذا الوصف يمنع التعميم ويجعل المقارنة لاحقًا أكثر عدلًا. لا تغيّر عدة عوامل في الوقت نفسه؛ اختر تعديلًا واحدًا يمكن تطبيقه باستمرار، مثل تقليل عدد التعليمات، تعديل التوقيت، تهيئة المكان، تقسيم المهمة، أو إضافة استراحة متفق عليها.</p>

  <h2>خطة تطبيق من سبع مراحل</h2>
  <ol class="tip237-steps">
    <li><strong>حدّد الأولوية:</strong> اختر موقفًا متكررًا يؤثر بوضوح في السلامة أو المشاركة أو الراحة، ولا تبدأ بأصعب المواقف كلها معًا.</li>
    <li><strong>صف خط الأساس:</strong> سجّل التكرار والمدة والشدة والحاجة إلى المساندة خلال عدة أيام، مع احترام الخصوصية وعدم جمع تفاصيل لا حاجة لها.</li>
    <li><strong>اختر دليلًا واحدًا:</strong> اقرأ هدف الدليل، وما يناسبه وما لا يناسبه، ثم استخرج خطوة واحدة قابلة للتطبيق في سياقك.</li>
    <li><strong>هيّئ البيئة:</strong> عدّل العوائق قبل مطالبة الشخص ببذل جهد إضافي؛ راجع الضوضاء والإضاءة والازدحام والوقت واللغة المستخدمة وتوقعات المهمة.</li>
    <li><strong>طبّق باتفاق واضح:</strong> استخدم جملة قصيرة ومحترمة، وحدّد من يفعل ماذا ومتى، واترك مساحة للاختيار والرفض الآمن كلما أمكن.</li>
    <li><strong>راقب الأثر:</strong> قارن المؤشرات نفسها التي سجلتها في خط الأساس، ولا تعتبر يومًا جيدًا أو صعبًا حكمًا نهائيًا على الخطة.</li>
    <li><strong>راجع وعدّل:</strong> احتفظ بما حسّن الوظيفة أو خفّف الضيق، وعدّل خطوة واحدة فقط عند غياب الأثر، واطلب مساعدة متخصصة عند استمرار التعطل.</li>
  </ol>

  <h2>تكييف المسار بحسب العمر والقدرة والسياق</h2>
  <p>للأطفال، استخدم لغة ملموسة وخيارات محدودة وروتينًا بصريًا ومشاركة من مقدم الرعاية دون تحويل المتابعة إلى مراقبة عقابية. للمراهقين، احترم الخصوصية وشاركهم في تحديد الهدف والمؤشر المقبول، وتجنب المناقشة الحساسة أمام الآخرين. للبالغين، اربط الخطة بالاستقلال والوقت والعمل والعلاقات والمسؤوليات الواقعية، ولا تفترض أن الأسرة هي صاحبة القرار.</p>
  <p>عندما توجد اختلافات في التواصل أو الانتباه أو المعالجة الحسية أو الحركة، عدّل طريقة تقديم الخطوة بدل تفسير صعوبة التنفيذ على أنها رفض أو كسل. يمكن استخدام نص مكتوب، صورة، نموذج عملي، وقت أطول للمعالجة، أو تقسيم المهمة إلى أجزاء. في المدرسة أو مكان العمل، حدّد التعديل المطلوب والنتيجة الوظيفية المتوقعة دون مشاركة معلومات صحية أكثر مما يلزم.</p>

  <h2>مؤشرات متابعة عملية</h2>
  <ul>
    <li>هل انخفضت مدة الضيق أو أصبح التعافي أسرع بعد الموقف؟</li>
    <li>هل زادت المشاركة أو القدرة على بدء المهمة أو إكمال جزء منها؟</li>
    <li>هل انخفضت الحاجة إلى التذكير أو التدخل المباشر أو الانسحاب؟</li>
    <li>هل أصبحت التوقعات أوضح، وهل قل الخلاف حول ما سيحدث بعد ذلك؟</li>
    <li>هل يمكن المحافظة على الخطوة دون استنزاف الشخص أو الأسرة أو مقدم الخدمة؟</li>
  </ul>
  <p>راجع المؤشرات أسبوعيًا أو وفق طبيعة الموقف. التحسن الواقعي قد يكون تدريجيًا وغير خطي؛ لذلك انظر إلى الاتجاه العام وإلى جودة الحياة، لا إلى رقم منفرد. إذا تحسن مؤشر وتدهور آخر، ناقش التوازن بدل إعلان نجاح كامل أو فشل كامل.</p>

  <h2>حدود السلامة ومتى تنتقل إلى مساعدة متخصصة</h2>
  <p>هذه الأدلة للتثقيف والتنظيم الأولي ولا تستبدل التقييم الفردي. اطلب مساعدة مهنية عندما تستمر الصعوبة أو تؤثر بوضوح في النوم أو الأكل أو الدراسة أو العمل أو العلاقات، أو عندما لا تكفي التعديلات البيئية والخطوات المنزلية. لا تبدأ دواءً أو توقفه ولا تغيّر جرعته اعتمادًا على دليل عام.</p>
  <p>عند وجود خطر فوري، أو أفكار لإيذاء النفس أو الآخرين، أو فقدان شديد للاتصال بالواقع، أو عنف، أو عجز عن تأمين الاحتياجات الأساسية، انتقل إلى خدمات الطوارئ المحلية أو جهة صحية مؤهلة فورًا. اجعل السلامة أولوية، وابتعد عن المواجهة التي قد تزيد الخطر، واطلب دعم شخص موثوق عند الإمكان.</p>

  <h2>طريقة اختيار الدليل التالي</h2>
  <p>بعد تجربة الخطوة الأولى، اختر الدليل التالي بناءً على النتيجة لا على العنوان الأكثر إثارة. إذا كانت المشكلة الأساسية هي البيئة، انتقل إلى دليل التهيئة أو الروتين. إذا كان العائق هو التواصل، اختر دليل الجمل الجاهزة أو الاستماع. إذا استمر التعطل رغم التطبيق المتسق، انتقل إلى دليل التحضير للموعد المهني واجمع ملاحظات مختصرة عن خط الأساس والخطوات المجربة وأثرها. بهذه الطريقة يصبح مسار {safe_title} سلسلة قرارات قابلة للمراجعة، لا مجموعة نصائح متفرقة.</p>
</section>
{TOPIC_END}
"""


def _search_script() -> str:
    return f"""
{SEARCH_START}
<script id="practical-tips-v248-search">
(() => {{
  const input = document.getElementById('tips-search');
  const cards = Array.from(document.querySelectorAll('[data-search]'));
  if (!input || cards.length === 0) return;
  let status = document.querySelector('[data-practical-tips-search-status]');
  if (!status) {{
    status = document.createElement('p');
    status.dataset.practicalTipsSearchStatus = '';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.className = 'tip237-search-status';
    input.insertAdjacentElement('afterend', status);
  }}
  const normalize = value => String(value || '')
    .normalize('NFKD')
    .replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
    .replace(/[أإآٱ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .toLocaleLowerCase('ar')
    .replace(/\s+/g, ' ')
    .trim();
  const filter = () => {{
    const query = normalize(input.value);
    let visible = 0;
    for (const card of cards) {{
      const haystack = normalize(`${{card.dataset.search || ''}} ${{card.textContent || ''}}`);
      const matches = !query || haystack.includes(query);
      card.hidden = !matches;
      card.setAttribute('aria-hidden', matches ? 'false' : 'true');
      if (matches) visible += 1;
    }}
    status.textContent = query
      ? `تم العثور على ${{visible}} من أصل ${{cards.length}} دليلًا.`
      : `تظهر جميع الأدلة وعددها ${{cards.length}}.`;
  }};
  input.addEventListener('input', filter);
  input.addEventListener('search', filter);
  filter();
}})();
</script>
{SEARCH_END}
"""


def _insert_before_closing_container(source: str, block: str, path: Path) -> str:
    insertion = source.lower().rfind("</main>")
    if insertion < 0:
        insertion = source.lower().rfind("</body>")
    if insertion < 0:
        raise RuntimeError(f"Missing main/body closing tag in {path}")
    return source[:insertion] + block + "\n" + source[insertion:]


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
    source = _insert_before_closing_container(source, _compatibility_block(heading), path)
    path.write_text(source, encoding="utf-8")


def _postprocess_topic(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    source = re.sub(
        re.escape(TOPIC_START) + r".*?" + re.escape(TOPIC_END),
        "",
        source,
        flags=re.S,
    )
    heading = _extract_h1(source, path.parent.name.replace("-", " "))
    source = _insert_before_closing_container(source, _topic_depth_block(heading), path)
    path.write_text(source, encoding="utf-8")


def _install_index_search(site: Path) -> dict[str, int | str]:
    path = site / "tips" / "index.html"
    if not path.is_file():
        raise RuntimeError("Practical tips index is missing")
    source = path.read_text(encoding="utf-8")
    source = re.sub(
        re.escape(SEARCH_START) + r".*?" + re.escape(SEARCH_END),
        "",
        source,
        flags=re.S,
    )
    if not re.search(r'<input\b[^>]*\bid=["\']tips-search["\']', source, flags=re.I | re.S):
        raise RuntimeError("Practical tips search input is missing")
    card_count = len(re.findall(r"\bdata-search\s*=", source, flags=re.I))
    if card_count != 100:
        raise RuntimeError(f"Practical tips search requires one hundred cards: {card_count}")
    closing = source.lower().rfind("</body>")
    if closing < 0:
        raise RuntimeError("Practical tips index body closing tag is missing")
    source = source[:closing] + _search_script() + "\n" + source[closing:]
    path.write_text(source, encoding="utf-8")
    updated = path.read_text(encoding="utf-8")
    if updated.count(SEARCH_START) != 1 or updated.count(SEARCH_END) != 1:
        raise RuntimeError("Practical tips search contract is missing or duplicated")
    return {
        "search_contract": "local-normalized-filter-v248",
        "search_cards": card_count,
    }


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


def _apply_topic_depth(site: Path) -> dict[str, int | str]:
    pages = sorted((site / "tips" / "topics").glob("*/index.html"))
    if len(pages) != 10:
        raise RuntimeError(f"Practical tips require exactly ten topic pages: {len(pages)}")
    for page in pages:
        _postprocess_topic(page)

    lengths: list[int] = []
    for page in pages:
        source = page.read_text(encoding="utf-8")
        if source.count(TOPIC_START) != 1 or source.count(TOPIC_END) != 1:
            raise RuntimeError(f"Topic depth block is missing or duplicated: {page}")
        for marker in (
            "كيف تستخدم مسار",
            "خطة تطبيق من سبع مراحل",
            "تكييف المسار بحسب العمر والقدرة والسياق",
            "مؤشرات متابعة عملية",
            "حدود السلامة ومتى تنتقل إلى مساعدة متخصصة",
            "طريقة اختيار الدليل التالي",
        ):
            if marker not in source:
                raise RuntimeError(f"Topic methodology heading is missing ({marker}): {page}")
        visible_characters = len(_plain(source))
        lengths.append(visible_characters)
        if visible_characters < TOPIC_MINIMUM_CHARACTERS:
            raise RuntimeError(
                f"Topic page is below institutional depth: {page} "
                f"({visible_characters} < {TOPIC_MINIMUM_CHARACTERS})"
            )
        for phrase in ("شفاء مضمون", "يعالج نهائيًا", "بديل عن الطبيب", "تشخيصك هو", "معاقين"):
            if phrase in source:
                raise RuntimeError(f"Unsafe or stigmatizing phrase in topic page ({phrase}): {page}")

    return {
        "topic_depth_status": "passed",
        "topic_depth_pages": len(pages),
        "minimum_topic_characters": min(lengths),
    }


def publish(site: Path | str, repo: Path | str = ROOT) -> dict:
    site_path = Path(site)
    report = _PACKED_PUBLISH(site_path, Path(repo))
    compatibility = _apply_core_compatibility(site_path)
    topic_depth = _apply_topic_depth(site_path)
    search_contract = _install_index_search(site_path)
    report = dict(report)
    report.update(compatibility)
    report.update(topic_depth)
    report.update(search_contract)
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
