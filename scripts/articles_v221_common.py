from __future__ import annotations
import html,json,re
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'content/v221/articles/normal-anxiety-vs-anxiety-disorder-ar.json'
STYLE_FILE=ROOT/'content/v221/articles/marshmallow-v221.css'
BASE='https://khaledaltheeb.github.io/pterminology-site/'
ROUTE='articles/normal-anxiety-vs-anxiety-disorder/'
URL=BASE+ROUTE
INDEX=BASE+'articles/'
NAME='منصة الصحة النفسية وذوي الاحتياجات الخاصة'
IMAGE=BASE+'assets/brand/social-card.svg'
HOSTS={'www.who.int','www.nimh.nih.gov','www.nice.org.uk','www.nhs.uk'}

def e(v): return html.escape(str(v),quote=True)

def load():
    d=json.loads(SRC.read_text(encoding='utf-8'))
    required={'title','description','summary','review_status','publication_status','risk_level','reviewed_at','keywords','quick_answer','comparison','sections','myths','seven_day_fields','internal_links','sources'}
    missing=required-set(d)
    if missing: raise SystemExit(f'missing fields: {sorted(missing)}')
    if (d['review_status'],d['publication_status'],d['risk_level'])!=('internally-reviewed','approved-for-build','moderate'): raise SystemExit('article state is not publishable')
    if not 90<=len(d['description'])<=180: raise SystemExit('invalid description')
    if not 4<=len(d['sources'])<=8: raise SystemExit('invalid sources')
    if any(urlparse(x['url']).scheme!='https' or urlparse(x['url']).hostname not in HOSTS for x in d['sources']): raise SystemExit('unapproved source')
    text=' '.join(d['quick_answer']+[x['normal']+' '+x['concern'] for x in d['comparison']]+[p for s in d['sections'] for p in s['paragraphs']]+[x['myth']+' '+x['fact'] for x in d['myths']])
    if len(re.findall(r'[\u0600-\u06FF]+',text))<1400: raise SystemExit('article too short')
    if any(x in text for x in ('تشخيصك هو','يعالج نهائيًا','يضمن الشفاء','بديل عن الطبيب')): raise SystemExit('unsafe claim')
    return d

def meta(title,desc,canonical,keys,schema,kind='article'):
    full=f'{title} | {NAME}'
    structured=json.dumps(schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    css=STYLE_FILE.read_text(encoding='utf-8')
    return f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(full)}</title><meta name="description" content="{e(desc)}"><meta name="keywords" content="{e(','.join(keys[:10]))}"><meta name="author" content="{NAME}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="theme-color" content="#edf8f5"><meta name="color-scheme" content="light"><link rel="canonical" href="{canonical}"><link rel="manifest" href="/pterminology-site/manifest.webmanifest"><link rel="icon" href="/pterminology-site/assets/brand/logo-mark.svg" type="image/svg+xml"><link rel="search" type="application/opensearchdescription+xml" title="البحث في المنصة" href="/pterminology-site/opensearch.xml"><link rel="sitemap" type="application/xml" href="{BASE}sitemap.xml"><meta property="og:type" content="{kind}"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="{NAME}"><meta property="og:title" content="{e(full)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{IMAGE}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(full)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{IMAGE}"><script type="application/ld+json">{structured}</script><style>{css}</style>'''

def head():
    return f'''<header class="top"><div class="wrap"><div class="brand">{NAME}</div><nav class="nav" aria-label="التنقل الرئيسي"><a href="/pterminology-site/">الرئيسية</a><a href="/pterminology-site/articles/">المقالات</a><a href="/pterminology-site/encyclopedia/">الموسوعة</a><a href="/pterminology-site/comparisons/">المقارنات</a><a href="/pterminology-site/care-guides/">أدلة التعامل</a><a href="/pterminology-site/trust/">المنهجية</a></nav></div></header>'''

def foot():
    return '''<footer class="foot"><div class="wrap"><p><strong>معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</strong></p><p>الاسم المؤسس: مصطلحات علم النفس. المحتوى للتثقيف العام ولا يستبدل التقييم أو العلاج الفردي.</p></div></footer>'''
