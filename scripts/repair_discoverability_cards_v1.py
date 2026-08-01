#!/usr/bin/env python3
from pathlib import Path
import html

ROOT = Path(__file__).resolve().parents[1]
STYLE_MARKER = '/* pt-discoverability-cards:v1 */'
SECTION_MARKER = 'data-pt-discoverability-cards="v1"'

HUBS = {
    'sections/index.html': {
        'id': 'institutional-access-points',
        'eyebrow': 'بوابات مؤسسية وخدمات مساندة',
        'title': 'صفحات أساسية يجب أن تبقى ظاهرة',
        'intro': 'وصول مباشر إلى أدلة الأسرة والبحث والتواصل والحوكمة والمصادر والفريق، مع وصف واضح لغرض كل صفحة.',
        'cards': [
            ('دليل الأسرة للرعاية والدعم', '64 دليلًا للحالات النمائية والعصبية والحركية والحسية والوراثية، مع خطوات عملية وخطط متابعة وأدوات للأسرة.', '/family-guide/', 'الأسر ومقدمو الرعاية'),
            ('البحث الذكي في المنصة', 'ابحث باللغة الطبيعية داخل محتوى المنصة للوصول إلى الصفحات الأقرب إلى السؤال أو الحالة أو الدليل المطلوب.', '/ai-search/', 'اكتشاف المحتوى'),
            ('تواصل معنا', 'القناة الرسمية للاستفسارات والشراكات والأبحاث والتصحيحات العلمية والدعم التقني والإتاحة والخصوصية.', '/contact/', 'تواصل رسمي'),
            ('سجل المصادر ومسارات التكامل', 'بوابة شفافة للمصادر المسجلة وواجهات البيانات ومسارات التكامل والتحقق من مرجعية المحتوى.', '/source-registry/', 'شفافية المصادر'),
            ('الفريق والشركاء ذوو الاختصاص', 'صفحة تعريفية بالفريق والشراكات المهنية ومسارات التعاون المرتبطة بالمنصة.', '/team-and-partners/', 'تعاون مهني'),
            ('الإتاحة وخطة التوافق', 'إفادة الإتاحة، وسائل الاستخدام الميسر، وآلية الإبلاغ عن عائق يمنع الوصول إلى المحتوى أو الوظائف.', '/accessibility/', 'إتاحة رقمية'),
        ],
    },
    'learning-paths/index.html': {
        'id': 'learning-opportunities',
        'eyebrow': 'تطبيق وتعاون',
        'title': 'فرص التدريب والتعاون المؤسسي',
        'intro': 'مسار واضح للجهات والمختصين والطلاب الراغبين في التدريب أو التعاون أو المساهمة المنهجية.',
        'cards': [
            ('فرص التدريب والتعاون', 'استعرض مجالات التدريب والتعاون المؤسسي والمساهمة العلمية وشروط التواصل والمعلومات التي يجب تجهيزها.', '/learning-paths/opportunities/', 'فرص وتعاون'),
        ],
    },
    'provider-assessment-demo/index.html': {
        'id': 'provider-professional-paths',
        'eyebrow': 'التطوير المهني',
        'title': 'التدريب والسجل المهني',
        'intro': 'بوابتان لمقدمي الخدمة والمراكز: تدريب منظم على التقييم، وسجل مهني للمقاييس والفحوص ومسارات الاستخدام المسؤول.',
        'cards': [
            ('أكاديمية التقييم المهني', 'تدريب المراكز ومقدمي الخدمة على مبادئ التقييم متعدد المصادر، اختيار الأدوات، التوثيق، وحدود التفسير.', '/provider-assessment-demo/training/', 'تدريب مهني'),
            ('السجل المهني للمقاييس والفحوص', 'واجهة منظمة للمقاييس والفحوص والمجالات المهنية، مع ضوابط الاستخدام والترخيص والتفسير المسؤول.', '/provider-assessment-demo/professional-console.html', 'سجل مهني'),
        ],
    },
    'special-needs/index.html': {
        'id': 'special-needs-featured-guides',
        'eyebrow': 'أدلة متخصصة',
        'title': 'تقنيات مساعدة ودليل حالة موسع',
        'intro': 'وصول مباشر إلى منظومة اختيار التقنيات المساعدة وإلى دليل متكامل لمتلازمة برادر ويلي عبر مراحل الحياة.',
        'cards': [
            ('التقنيات المساعدة', 'دليل الاختيار والتقييم والتجربة والأمان والتدريب والصيانة، مع مسارات أخلاقية وتعليم مستمر.', '/special-needs/assistive-technology/', 'تقنيات مساعدة'),
            ('متلازمة برادر ويلي', 'دليل للأسرة والمختصين حول الصحة والتغذية والسلوك والتعليم والمتابعة والدعم عبر مراحل الحياة.', '/special-needs/conditions/prader-willi-syndrome/', 'دليل حالة'),
        ],
    },
    'special-needs/assistive-technology/index.html': {
        'id': 'assistive-technology-professional-guides',
        'eyebrow': 'مسارات تطبيقية ومهنية',
        'title': 'أدلة التقنيات المساعدة المتخصصة',
        'intro': 'مسارات عملية تساعد الأسرة والمختص ومقدم الخدمة على الاختيار الأخلاقي، تقييم الابتكار، التدريب، والتعليم المستمر.',
        'cards': [
            ('قائمة فحص اختيار التقنية المساعدة', 'خطوات منظمة للتقييم والتجربة والملاءمة والأمان والصيانة قبل اعتماد أي تقنية أو جهاز.', '/special-needs/assistive-technology/selection-checklist/', 'اختيار وتقييم'),
            ('مسار التدريب في التقنيات المساعدة', 'خطة تدريب للمستخدم والأسرة والفريق لضمان الاستخدام الفعلي والآمن ومراجعة النتائج.', '/special-needs/assistive-technology/training/', 'تدريب المستخدم'),
            ('أخلاقيات وجودة الخدمة', 'إطار لتقديم خدمات تحترم الحقوق والاختيار والخصوصية والكفاءة المهنية والمتابعة.', '/special-needs/assistive-technology/ethics-and-service/', 'أخلاقيات وجودة'),
            ('مراجعة ابتكارات التقنيات المساعدة', 'بوابة علمية وأخلاقية لفحص الادعاءات والجدوى والمخاطر قبل التجربة أو التوصية أو النشر.', '/special-needs/assistive-technology/innovation-review/', 'ابتكار مسؤول'),
            ('التعليم المستمر والتحقق من الدورات', 'دليل للتحقق من الدورات والمزودين ومسارات التعليم المستمر المرتبطة بالممارسة المهنية.', '/special-needs/assistive-technology/continuing-education/', 'تعليم مستمر'),
        ],
    },
}

CSS = r'''

/* pt-discoverability-cards:v1 */
.pt-discovery-section{width:min(var(--pt-content),calc(100% - 28px));margin:2.75rem auto 0;padding:clamp(1.15rem,3vw,2rem);border:1px solid var(--pt-line);border-radius:calc(var(--pt-radius) + 4px);background:linear-gradient(145deg,rgba(242,250,248,.96),rgba(255,255,255,.98));box-shadow:var(--pt-shadow)}
.pt-discovery-section__eyebrow{margin:0 0 .25rem;color:var(--pt-accent);font-size:.88rem;font-weight:900;letter-spacing:.02em}
.pt-discovery-section h2{margin:0;font-size:clamp(1.55rem,3.2vw,2.35rem)}
.pt-discovery-section__intro{margin:.55rem 0 0;color:var(--pt-muted)}
.pt-discovery-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,245px),1fr));gap:1rem;margin-top:1.35rem}
.pt-discovery-card{display:flex;flex-direction:column;min-height:225px;padding:1.15rem;border:1px solid var(--pt-line);border-radius:var(--pt-radius);background:var(--pt-surface);box-shadow:0 8px 22px rgba(10,72,71,.07)}
.pt-discovery-card__tag{align-self:flex-start;padding:.2rem .65rem;border:1px solid #a9d5d0;border-radius:999px;background:var(--pt-surface-soft);color:var(--pt-brand-strong);font-size:.78rem;font-weight:900}
.pt-discovery-card h3{margin:.7rem 0 .35rem;font-size:1.18rem}
.pt-discovery-card p{flex:1;margin:0 0 1rem;color:var(--pt-muted)}
.pt-discovery-card a{align-self:flex-start;min-height:44px;display:inline-flex;align-items:center;padding:.55rem .85rem;border-radius:10px;background:var(--pt-brand);color:#fff!important;font-weight:900;text-decoration:none}
.pt-discovery-card a:hover{background:var(--pt-brand-strong);color:#fff!important}
@media(max-width:640px){.pt-discovery-section{width:min(100% - 18px,var(--pt-content))}.pt-discovery-card{min-height:0}}
'''


def section_html(spec):
    cards = []
    for title, description, href, tag in spec['cards']:
        cards.append(f'''<article class="pt-discovery-card">
<span class="pt-discovery-card__tag">{html.escape(tag)}</span>
<h3>{html.escape(title)}</h3>
<p>{html.escape(description)}</p>
<a href="{html.escape(href, quote=True)}">فتح الصفحة <span aria-hidden="true">←</span></a>
</article>''')
    sid = html.escape(spec['id'], quote=True)
    return f'''
<section class="pt-discovery-section" data-pt-discoverability-cards="v1" id="{sid}" aria-labelledby="{sid}-title">
<p class="pt-discovery-section__eyebrow">{html.escape(spec['eyebrow'])}</p>
<h2 id="{sid}-title">{html.escape(spec['title'])}</h2>
<p class="pt-discovery-section__intro">{html.escape(spec['intro'])}</p>
<div class="pt-discovery-grid">
{''.join(cards)}
</div>
</section>
'''


def apply():
    css_path = ROOT / 'assets/platform/platform-core.css'
    css = css_path.read_text(encoding='utf-8')
    if STYLE_MARKER not in css:
        css_path.write_text(css + CSS, encoding='utf-8')

    for rel, spec in HUBS.items():
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f'missing hub: {rel}')
        text = path.read_text(encoding='utf-8')
        if SECTION_MARKER not in text:
            pos = text.lower().rfind('</main>')
            if pos < 0:
                raise SystemExit(f'no </main> in {rel}')
            text = text[:pos] + section_html(spec) + text[pos:]
        text = text.replace('platform-core.css?v=1.1.0', 'platform-core.css?v=1.2.0')
        path.write_text(text, encoding='utf-8')

    test_path = ROOT / 'tests/test_user_discoverability_cards_v1.py'
    test_path.write_text(TEST, encoding='utf-8')
    print({'hubs': len(HUBS), 'cards': sum(len(x['cards']) for x in HUBS.values())})


TEST = '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "sections/index.html": ["/family-guide/", "/ai-search/", "/contact/", "/source-registry/", "/team-and-partners/", "/accessibility/"],
    "learning-paths/index.html": ["/learning-paths/opportunities/"],
    "provider-assessment-demo/index.html": ["/provider-assessment-demo/training/", "/provider-assessment-demo/professional-console.html"],
    "special-needs/index.html": ["/special-needs/assistive-technology/", "/special-needs/conditions/prader-willi-syndrome/"],
    "special-needs/assistive-technology/index.html": ["/special-needs/assistive-technology/selection-checklist/", "/special-needs/assistive-technology/training/", "/special-needs/assistive-technology/ethics-and-service/", "/special-needs/assistive-technology/innovation-review/", "/special-needs/assistive-technology/continuing-education/"],
}

def test_all_hidden_pages_have_static_section_cards():
    total = 0
    for rel, targets in EXPECTED.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert text.count('data-pt-discoverability-cards="v1"') == 1, rel
        for target in targets:
            assert f'href="{target}"' in text, (rel, target)
            total += 1
    assert total == 16

def test_cards_are_semantic_and_descriptive():
    for rel, targets in EXPECTED.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        section = text.split('data-pt-discoverability-cards="v1"', 1)[1].split('</section>', 1)[0]
        assert section.count('<article class="pt-discovery-card">') == len(targets)
        assert section.count('<h3>') == len(targets)
        assert section.count('فتح الصفحة') == len(targets)

def test_shared_card_styles_are_versioned():
    css = (ROOT / "assets/platform/platform-core.css").read_text(encoding="utf-8")
    assert css.count('/* pt-discoverability-cards:v1 */') == 1
    for rel in EXPECTED:
        assert 'platform-core.css?v=1.2.0' in (ROOT / rel).read_text(encoding="utf-8")
'''

if __name__ == '__main__':
    apply()
