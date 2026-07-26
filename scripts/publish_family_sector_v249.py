#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import upgrade_family_sector_v249 as core

_ORIGINAL_NORMALIZE_HEAD = core.normalize_head
_ORIGINAL_ARTICLE_SCHEMA = core.article_schema
_ORIGINAL_HUB_MAIN = core.hub_main


def normalize_head(source: str, *, article: bool = False, **kwargs: Any) -> str:
    source = re.sub(
        r'<script\b[^>]*data-family-article-v249-schema=["\'][^"\']+["\'][^>]*>.*?</script>',
        "",
        source,
        flags=re.I | re.S,
    )
    return _ORIGINAL_NORMALIZE_HEAD(source, article=article, **kwargs)


def article_schema(item: dict[str, Any]) -> str:
    return _ORIGINAL_ARTICLE_SCHEMA(item).replace(
        "data-family-article-v249-schema",
        "data-family-article-schema-v249",
        1,
    )


def hub_main(data: dict[str, Any]) -> str:
    source = _ORIGINAL_HUB_MAIN(data)
    block = '''
<section class="fv-section" id="review"><div class="fv-wrap"><h2>المراجعة الأسرية القائمة على الأدلة لا الانطباعات</h2>
<p>تحتاج الخطة الأسرية إلى مراجعة منتظمة تمنع طرفين متعاكسين: الاستمرار في أسلوب لا يعمل لمجرد أنه مألوف، وتغيير كل شيء بسرعة قبل معرفة ما الذي ساعد. تختار الأسرة مؤشرين أو ثلاثة يمكن ملاحظتها، مثل عدد مرات التصعيد خلال الأسبوع، والوقت اللازم للعودة إلى الحوار، والقدرة على إنجاز الروتين الأساسي، وشعور كل فرد بالأمان والمشاركة. لا تُستخدم الأرقام لإدانة شخص، بل لفهم ما إذا كان النظام الجديد أخف ضررًا وأكثر وضوحًا.</p>
<p>تُعقد المراجعة في وقت هادئ وبمدة محدودة. يبدأ كل مشارك بوصف ما لاحظه، ثم يذكر شيئًا ساعد وشيئًا يحتاج تعديلًا. تُعطى الأولوية لصوت الشخص الأكثر تأثرًا، مع إتاحة الكتابة أو الإشارة أو الدعم البصري أو وجود مرافق يختاره عند الحاجة. إذا اختلفت الروايات، لا تُحسم المسألة بالسلطة وحدها؛ تُفصل الوقائع القابلة للملاحظة عن التفسير، ويُبحث عن بيانات إضافية أو رأي مهني محايد.</p>
<p>تشمل المراجعة البيئة لا السلوك فقط: هل كان الوقت مناسبًا؟ هل كانت التعليمات كثيرة؟ هل توجد ضوضاء أو ألم أو تعب أو ضغط مالي أو عبء رعاية لم يُعالج؟ قد يكون التعديل الأفضل نقل مسؤولية، أو حماية النوم، أو تقليل عدد القرارات، أو توفير وسيلة تواصل، لا مطالبة الفرد بمزيد من ضبط النفس.</p>
<p>في نهاية المراجعة تُكتب ثلاثة قرارات: ما الذي سيستمر، وما الذي سيُبسط، وما الذي يحتاج دعمًا خارجيًا. يُحدد مالك كل خطوة وموعدها وطريقة قياسها. إذا كشفت المراجعة خوفًا أو عنفًا أو نية للإيذاء أو تدهورًا واضحًا في الوظائف اليومية، لا تُؤجل الاستجابة إلى الاجتماع التالي؛ تُفعل خطة السلامة ويُطلب مستوى الرعاية المناسب فورًا.</p>
</div></section>
'''
    if source.count("</main>") != 1:
        raise ValueError("family_hub_main_contract")
    return source.replace("</main>", block + "</main>", 1)


core.normalize_head = normalize_head
core.article_schema = article_schema
core.hub_main = hub_main

visible_words = core.visible_words
article_main = core.article_main
DEFAULT_SOURCE = core.DEFAULT_SOURCE
REPORT_NAME = core.REPORT_NAME
VERSION = core.VERSION


def upgrade(site: Path, source_path: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    return core.upgrade(site, source_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish the institutional family mental-health sector")
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    upgrade(args.site, args.source)


if __name__ == "__main__":
    main()
