#!/usr/bin/env python3
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib, html, json, re

ROOT = Path(__file__).resolve().parents[2]
SCOPES = [ROOT / 'special-needs', ROOT / 'inclusive-education']
TARGET = 50
SITE = 'https://healthrenewal.org/'
BRAND = 'منصة روافد'
EN = 'Health Renewal'
STATE = ROOT / '.github/seo/special-needs-seo-state.json'
MANIFEST = ROOT / '.github/seo/special-needs-semantic-manifest.json'
REPORT = ROOT / '.github/reports/seo-special-needs-latest.json'
BEGIN = '<!-- rawafid:technical-seo:v3 -->'
END = '<!-- /rawafid:technical-seo:v3 -->'
ANY_MARKER = re.compile(r'<!-- rawafid:technical-seo:v(?:2|3) -->')
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

CATEGORY_AR = {
    'special-needs': 'ذوو الاحتياجات الخاصة',
    'inclusive-education': 'التربية الدامجة',
    'education': 'التربية الخاصة والتعليم الدامج',
    'conditions': 'الحالات والمتلازمات',
    'practical': 'الأدلة العملية',
    'assistive-technology': 'التقنيات المساندة',
    'communication': 'التواصل',
    'aac': 'التواصل المعزز والبديل',
    'hearing': 'السمع',
    'learning': 'التعلم',
    'early-intervention': 'التدخل المبكر',
    'guides': 'الأدلة',
    'evidence': 'الأدلة العلمية',
}

def norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()

def visible_text(s):
    s = re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>', ' ', s, flags=re.I | re.S)
    return norm(html.unescape(re.sub(r'<[^>]+>', ' ', s)))

def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()

def rel(p):
    return p.relative_to(ROOT).as_posix()

def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def attrs(tag):
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in re.finditer(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2', tag, re.S)}

def meta(src, kind, key):
    for m in re.finditer(r'<meta\b[^>]*>', src, re.I | re.S):
        a = attrs(m.group())
        if a.get(kind, '').lower() == key.lower():
            return norm(a.get('content', ''))
    return ''

def link(src, relname):
    for m in re.finditer(r'<link\b[^>]*>', src, re.I | re.S):
        a = attrs(m.group())
        if relname.lower() in a.get('rel', '').lower().split():
            return norm(a.get('href', ''))
    return ''

def get_title(src):
    m = re.search(r'<title\b[^>]*>(.*?)</title>', src, re.I | re.S)
    return visible_text(m.group(1)) if m else ''

def get_h1(src):
    m = re.search(r'<h1\b[^>]*>(.*?)</h1>', src, re.I | re.S)
    return visible_text(m.group(1)) if m else ''

def html_lang(src):
    m = re.search(r'<html\b[^>]*>', src, re.I | re.S)
    return attrs(m.group()).get('lang', '') if m else ''

def body(src):
    m = re.search(r'<body\b', src, re.I)
    return src[m.start():] if m else ''

def body_hash(src):
    return sha(body(src))

def canonical_for(p):
    q = rel(p)
    if q.endswith('index.html'):
        q = q[:-10]
    return SITE + q.lstrip('/')

def insert_head(src, block):
    m = re.search(r'</head\s*>', src, re.I)
    return src[:m.start()] + block + '\n' + src[m.start():] if m else src

def replace_title(src, value):
    tag = '<title>' + html.escape(value) + '</title>'
    m = re.search(r'<title\b[^>]*>.*?</title>', src, re.I | re.S)
    if not m:
        return insert_head(src, tag), True
    return src[:m.start()] + tag + src[m.end():], m.group() != tag

def set_meta(src, kind, key, value, replace=False):
    for m in re.finditer(r'<meta\b[^>]*>', src, re.I | re.S):
        a = attrs(m.group())
        if a.get(kind, '').lower() == key.lower():
            if not replace:
                return src, False
            old = m.group()
            if re.search(r'\bcontent\s*=', old, re.I):
                new = re.sub(r'(\bcontent\s*=\s*)(["\'])(.*?)\2', lambda x: x.group(1) + x.group(2) + html.escape(value, quote=True) + x.group(2), old, count=1, flags=re.I | re.S)
            else:
                new = old[:-1] + f' content="{html.escape(value, quote=True)}">'
            return src[:m.start()] + new + src[m.end():], new != old
    return insert_head(src, f'<meta {kind}="{html.escape(key, quote=True)}" content="{html.escape(value, quote=True)}">'), True

def set_canonical(src, value):
    for m in re.finditer(r'<link\b[^>]*>', src, re.I | re.S):
        a = attrs(m.group())
        if 'canonical' in a.get('rel', '').lower().split():
            old = m.group()
            if re.search(r'\bhref\s*=', old, re.I):
                new = re.sub(r'(\bhref\s*=\s*)(["\'])(.*?)\2', lambda x: x.group(1) + x.group(2) + html.escape(value, quote=True) + x.group(2), old, count=1, flags=re.I | re.S)
            else:
                new = old[:-1] + f' href="{html.escape(value, quote=True)}">'
            return src[:m.start()] + new + src[m.end():], new != old
    return insert_head(src, f'<link rel="canonical" href="{html.escape(value, quote=True)}">'), True

def set_lang_ar(src):
    m = re.search(r'<html\b[^>]*>', src, re.I | re.S)
    if not m:
        return src, False
    old = m.group()
    if re.search(r'\blang\s*=', old, re.I):
        new = re.sub(r'(\blang\s*=\s*)(["\'])(.*?)\2', r'\1\2ar\2', old, count=1, flags=re.I | re.S)
    else:
        new = old[:-1] + ' lang="ar">'
    return src[:m.start()] + new + src[m.end():], new != old

def first_para(src):
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>', body(src), re.I | re.S):
        t = visible_text(m.group(1))
        if len(t) >= 70 and not t.startswith(('محرك المحتوى', 'مراجعة داخلية', 'تنبيه', 'ملاحظة')):
            return t
    return ''

def trim(s, n=158):
    s = norm(s)
    if len(s) <= n:
        return s
    return s[:n - 1].rsplit(' ', 1)[0].rstrip('،؛:.-') + '…'

def base_title(src):
    t = get_title(src) or get_h1(src) or 'صفحة معرفية'
    t = re.sub(r'\s*[|｜]\s*(?:منصة\s+)?روافد\s*$', '', t, flags=re.I)
    t = re.sub(r'\s*[|｜]\s*Health\s+Renewal\s*$', '', t, flags=re.I)
    return norm(t)

def category_label(path):
    parts = Path(path).parts
    for part in reversed(parts[:-1]):
        if part in CATEGORY_AR:
            return CATEGORY_AR[part]
    return 'المعرفة المتخصصة'

def valid_jsonld(src):
    count = 0
    for i, m in enumerate(re.finditer(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', src, re.I | re.S), 1):
        count += 1
        try:
            json.loads(html.unescape(m.group(1)).strip())
        except Exception as exc:
            return False, f'json-ld-{i}:{exc}'
    return count > 0, '' if count else 'json-ld-missing'

def sitemap_text():
    out = []
    for p in ROOT.glob('sitemap*.xml'):
        try:
            out.append(p.read_text(encoding='utf-8', errors='ignore'))
        except Exception:
            pass
    return '\n'.join(out)

def headings(src):
    out = []
    for m in re.finditer(r'<h[1-3]\b[^>]*>(.*?)</h[1-3]>', src, re.I | re.S):
        t = visible_text(m.group(1))
        if 4 <= len(t) <= 120 and t not in out and not t.startswith(('المراجع', 'المصادر', 'المحتويات')):
            out.append(t)
    return out[:24]

def local_image_exists(url):
    if not url:
        return False
    if not url.startswith(SITE):
        return True
    p = ROOT / url[len(SITE):].split('?', 1)[0].lstrip('/')
    return p.is_file()

def semantic_queries(src, path):
    main = base_title(src)
    label = category_label(path)
    terms = [main] + headings(src)
    generic = [
        '{}', 'شرح {}', 'دليل {}', 'معلومات عن {}', '{} بالعربي', '{} بالتفصيل', 'أسئلة عن {}',
        'أسئلة شائعة عن {}', 'أفضل الممارسات في {}', 'أخطاء شائعة في {}', 'خطوات {}', 'طريقة {}',
        'كيفية {}', 'نصائح عن {}', 'مصادر موثوقة عن {}', 'دليل عملي عن {}', 'متى نحتاج إلى {}',
        'كيف نفهم {}', 'ما المقصود بـ {}', 'ما الذي يجب معرفته عن {}', '{} للأهل', '{} للأسرة',
        '{} للمعلمين', '{} للمدرسة', '{} للمتخصصين', '{} للأطفال', '{} للمراهقين', '{} للبالغين',
        'تقييم {}', 'دعم {}', 'خطة {}', 'استراتيجيات {}', 'أمثلة على {}', 'تطبيق {}', 'كيف نختار {}',
        'كيف نقيم {}', 'مؤشرات {}', 'معايير {}', '{} في المنزل', '{} في المدرسة', '{} في الصف',
        '{} والتربية الدامجة', '{} وذوو الاحتياجات الخاصة', '{} روافد', '{} Health Renewal'
    ]
    if '/conditions/' in '/' + path:
        specific = ['أعراض {}', 'علامات {}', 'أسباب {}', 'تشخيص {}', 'التشخيص المبكر لـ {}', 'فحوصات {}', 'تأهيل {}', 'التدخل المبكر لـ {}', 'متابعة {}', 'التعايش مع {}', 'دعم الأسرة في {}', 'التعليم مع {}', 'مضاعفات {}']
    elif any(x in '/' + path for x in ('/education/', '/inclusive-education/', '/iep-')):
        specific = ['{} في التعليم الدامج', '{} في التربية الخاصة', '{} للطلاب ذوي الاحتياجات الخاصة', 'تكييفات {}', 'تسهيلات {}', 'خطة فردية لـ {}', 'IEP و{}', 'UDL و{}', 'التصميم الشامل و{}', 'تقييم الطلاب في {}', 'استراتيجيات صفية لـ {}', 'دور المعلم في {}', 'قياس تقدم {}']
    elif any(x in '/' + path for x in ('/aac/', '/communication/', '/speech/', '/hearing/')):
        specific = ['تقييم التواصل في {}', 'تدخلات التواصل في {}', 'AAC و{}', 'لغة وتواصل {}', 'تدريب الأسرة على {}', 'أهداف تواصل في {}', 'أنشطة منزلية لـ {}', 'أنشطة مدرسية لـ {}', 'اختيار وسيلة التواصل لـ {}', 'التقنية المساندة في {}']
    elif '/assistive-technology/' in '/' + path:
        specific = ['اختيار التقنية المساندة لـ {}', 'تقييم التقنية المساندة في {}', 'تجربة التقنية المساندة لـ {}', 'تدريب المستخدم على {}', 'إتاحة {}', 'أجهزة مساندة لـ {}', 'حلول وصول لـ {}', 'متابعة فعالية {}']
    else:
        specific = ['دعم الأسرة في {}', 'دعم المدرسة في {}', 'خطة عملية لـ {}', 'قائمة تحقق لـ {}', 'أسئلة المختص عن {}', 'قرارات يومية في {}', 'قياس نتائج {}', 'متابعة تقدم {}']
    out, seen = [], set()
    def add(q):
        q = norm(q).strip(' -–—|،؛:.')
        k = q.casefold()
        if 3 <= len(q) <= 180 and k not in seen:
            seen.add(k)
            out.append(q)
    for term in terms:
        for pat in generic + specific:
            add(pat.format(term))
            if len(out) >= 500:
                return main, out[:500]
    variants = [main.replace('إ', 'ا').replace('أ', 'ا').replace('آ', 'ا'), main.replace('ة', 'ه'), main.replace('ى', 'ي')]
    for v in variants:
        if v != main:
            for p in ('{}', 'شرح {}', 'معلومات عن {}', '{} روافد'):
                add(p.format(v))
    suffix = ['شرح مبسط', 'شرح علمي', 'دليل شامل', 'دليل عملي', 'أسئلة وأجوبة', 'خطوات عملية', 'أخطاء يجب تجنبها', 'معايير الجودة', 'أفضل الممارسات', 'تقييم ومتابعة', 'خطة دعم', 'أمثلة تطبيقية', 'مصادر علمية', 'مصطلحات مهمة', 'نصائح عملية', 'مؤشرات المتابعة', 'قرارات عملية', 'أهداف قابلة للقياس', 'متابعة التقدم', 'حلول شائعة', 'متى نطلب مساعدة مختص']
    audience = ['للأهل', 'للأسرة', 'للمعلمين', 'للمدرسة', 'للمختصين', 'للطلاب', 'للأطفال', 'للمراهقين', 'للبالغين', 'لمقدمي الرعاية', 'لفريق الدعم', 'في المنزل', 'في الصف', 'في المدرسة', 'في التربية الدامجة', 'في التربية الخاصة', 'في الحياة اليومية']
    prefixes = ['', 'تعلم ', 'فهم ', 'تطبيق ', 'تقييم ', 'دعم ', 'متابعة ', 'دليل ', 'شرح ', 'خطة ', 'أسئلة عن ', 'معلومات عن ']
    for prefix in prefixes:
        for s in suffix:
            for a in audience:
                add(f'{prefix}{main} {s} {a}')
                if len(out) >= 500:
                    return f'{main} — {label}', out[:500]
    return f'{main} — {label}', out[:500]

def breadcrumb_nodes(can, title, path):
    parts = [p for p in Path(path).parts[:-1] if p != 'index.html']
    items = [{'@type': 'ListItem', 'position': 1, 'name': 'الرئيسية', 'item': SITE}]
    cur = SITE
    pos = 2
    for part in parts:
        cur += part + '/'
        items.append({'@type': 'ListItem', 'position': pos, 'name': CATEGORY_AR.get(part, part.replace('-', ' ')), 'item': cur})
        pos += 1
    items.append({'@type': 'ListItem', 'position': pos, 'name': title, 'item': can})
    return items

def choose_description(src, existing):
    candidate = trim(first_para(src) or get_h1(src) or base_title(src))
    if existing and 90 <= len(existing) <= 180:
        return existing
    return candidate or existing

def social_type(src):
    if re.search(r'"@type"\s*:\s*"(?:Article|MedicalWebPage|TechArticle|NewsArticle)"', src) or re.search(r'<article\b', src, re.I):
        return 'article'
    return 'website'

def enhance(src, p, duplicate_title=False, duplicate_desc=False):
    old_body = body(src)
    changes = []
    path = rel(p)
    bt = base_title(src)
    h1 = get_h1(src)
    label = category_label(path)
    current_title = get_title(src)
    target_title = current_title
    if not target_title:
        target_title = h1 or bt
    if duplicate_title:
        target_title = f'{h1 or bt} | {label} | {BRAND}'
    elif BRAND not in target_title and EN.lower() not in target_title.lower():
        target_title = target_title.rstrip(' |') + ' | ' + BRAND
    if target_title != current_title:
        src, c = replace_title(src, target_title)
        if c: changes.append('title')

    current_desc = meta(src, 'name', 'description')
    target_desc = choose_description(src, current_desc)
    if not current_desc or duplicate_desc:
        if duplicate_desc:
            target_desc = trim(f'{h1 or bt}: {first_para(src) or current_desc}')
        src, c = set_meta(src, 'name', 'description', target_desc, True)
        if c: changes.append('description')
    else:
        target_desc = current_desc

    expected_can = canonical_for(p)
    current_can = link(src, 'canonical')
    if not current_can:
        src, c = set_canonical(src, expected_can)
        if c: changes.append('canonical')
        current_can = expected_can
    elif current_can != expected_can and current_can.startswith(SITE):
        src, c = set_canonical(src, expected_can)
        if c: changes.append('canonical')
        current_can = expected_can

    robots = meta(src, 'name', 'robots')
    if not robots:
        src, c = set_meta(src, 'name', 'robots', 'index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1')
        if c: changes.append('indexability')
    elif 'noindex' not in robots.lower():
        additions = []
        if 'index' not in robots.lower(): additions.append('index')
        if 'follow' not in robots.lower(): additions.append('follow')
        if 'max-snippet' not in robots.lower(): additions.append('max-snippet:-1')
        if 'max-image-preview' not in robots.lower(): additions.append('max-image-preview:large')
        if 'max-video-preview' not in robots.lower(): additions.append('max-video-preview:-1')
        if additions:
            src, c = set_meta(src, 'name', 'robots', robots.rstrip(',') + ',' + ','.join(additions), True)
            if c: changes.append('indexability')

    if html_lang(src).lower() not in ('ar', 'ar-sa', 'ar-jo'):
        src, c = set_lang_ar(src)
        if c: changes.append('lang')

    img = meta(src, 'property', 'og:image')
    fallback = SITE + 'assets/brand/rawafid-social-card.jpg' if (ROOT / 'assets/brand/rawafid-social-card.jpg').is_file() else ''
    if not local_image_exists(img):
        img = fallback
    og_type = social_type(src)
    social = [
        ('name', 'application-name', BRAND),
        ('property', 'og:type', og_type),
        ('property', 'og:locale', 'ar_AR'),
        ('property', 'og:site_name', BRAND),
        ('property', 'og:title', target_title),
        ('property', 'og:description', target_desc),
        ('property', 'og:url', current_can),
        ('property', 'og:image', img),
        ('property', 'og:image:alt', bt),
        ('name', 'twitter:card', 'summary_large_image' if img else 'summary'),
        ('name', 'twitter:title', target_title),
        ('name', 'twitter:description', target_desc),
        ('name', 'twitter:image', img),
        ('name', 'twitter:image:alt', bt),
    ]
    for kind, key, value in social:
        if not value:
            continue
        old = meta(src, kind, key)
        if old != value:
            src, c = set_meta(src, kind, key, value, replace=bool(old))
            if c: changes.append('og-twitter' if key.startswith(('og:', 'twitter:')) else 'application-name')

    graph = {
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'Organization', '@id': SITE + '#organization', 'name': BRAND, 'alternateName': EN, 'url': SITE},
            {'@type': 'WebSite', '@id': SITE + '#website', 'url': SITE, 'name': BRAND, 'alternateName': EN, 'inLanguage': 'ar', 'publisher': {'@id': SITE + '#organization'}},
            {'@type': 'WebPage', '@id': current_can + '#webpage', 'url': current_can, 'name': target_title, 'description': target_desc, 'inLanguage': 'ar', 'isPartOf': {'@id': SITE + '#website'}, 'breadcrumb': {'@id': current_can + '#breadcrumb'}},
            {'@type': 'BreadcrumbList', '@id': current_can + '#breadcrumb', 'itemListElement': breadcrumb_nodes(current_can, bt, path)},
        ],
    }
    block = BEGIN + '\n<script type="application/ld+json">' + json.dumps(graph, ensure_ascii=False, separators=(',', ':')) + '</script>\n' + END
    m = re.search(re.escape(BEGIN) + r'.*?' + re.escape(END), src, re.S)
    if m:
        if m.group() != block:
            src = src[:m.start()] + block + src[m.end():]
            changes.append('schema')
    elif not ANY_MARKER.search(src):
        src = insert_head(src, block)
        changes.append('schema')

    if body(src) != old_body:
        return src, changes, 'visible-body-changed'
    ok, err = valid_jsonld(src)
    return src, sorted(set(changes)), '' if ok else err

def verify(src, p):
    expected_can = canonical_for(p)
    rob = meta(src, 'name', 'robots').lower()
    req = [
        get_title(src), meta(src, 'name', 'description'), link(src, 'canonical'), html_lang(src),
        meta(src, 'property', 'og:type'), meta(src, 'property', 'og:locale'), meta(src, 'property', 'og:site_name'),
        meta(src, 'property', 'og:title'), meta(src, 'property', 'og:description'), meta(src, 'property', 'og:url'),
        meta(src, 'name', 'twitter:card'), meta(src, 'name', 'twitter:title'), meta(src, 'name', 'twitter:description')
    ]
    if not all(req):
        return False, 'required-metadata-missing'
    if 'noindex' in rob:
        return False, 'noindex-present'
    if link(src, 'canonical') != expected_can:
        return False, 'canonical-mismatch'
    if meta(src, 'property', 'og:url') != expected_can:
        return False, 'og-url-mismatch'
    if meta(src, 'property', 'og:title') != get_title(src) or meta(src, 'name', 'twitter:title') != get_title(src):
        return False, 'social-title-mismatch'
    if meta(src, 'property', 'og:description') != meta(src, 'name', 'description') or meta(src, 'name', 'twitter:description') != meta(src, 'name', 'description'):
        return False, 'social-description-mismatch'
    img = meta(src, 'property', 'og:image')
    if img and not local_image_exists(img):
        return False, 'og-image-missing'
    ok, err = valid_jsonld(src)
    return ok, err

def material_issues(src, p, title_counts, desc_counts):
    issues = []
    title = get_title(src)
    desc = meta(src, 'name', 'description')
    t = norm(title).casefold()
    d = norm(desc).casefold()
    expected_can = canonical_for(p)
    current_can = link(src, 'canonical')
    robots = meta(src, 'name', 'robots').lower()
    if 'noindex' in robots:
        return ['blocked-existing-noindex']
    if not title or BRAND not in title and EN.lower() not in title.lower(): issues.append('title')
    if t and title_counts[t] > 1: issues.append('title-duplicate')
    if not desc: issues.append('description')
    if d and desc_counts[d] > 1: issues.append('description-duplicate')
    if not current_can: issues.append('canonical')
    elif current_can != expected_can:
        if current_can.startswith(SITE): issues.append('canonical-same-site-mismatch')
        else: return ['blocked-external-canonical']
    if not robots or any(x not in robots for x in ('index', 'follow', 'max-image-preview')): issues.append('indexability')
    if html_lang(src).lower() not in ('ar', 'ar-sa', 'ar-jo'): issues.append('lang')
    expected_title = title if title else (get_h1(src) or base_title(src)) + ' | ' + BRAND
    if meta(src, 'property', 'og:locale') != 'ar_AR' or meta(src, 'property', 'og:site_name') != BRAND: issues.append('og')
    if meta(src, 'property', 'og:url') != (current_can or expected_can): issues.append('og')
    if meta(src, 'property', 'og:title') != expected_title: issues.append('og')
    if meta(src, 'property', 'og:description') != desc: issues.append('og')
    if meta(src, 'name', 'twitter:title') != expected_title or meta(src, 'name', 'twitter:description') != desc: issues.append('twitter')
    img = meta(src, 'property', 'og:image')
    if img and not local_image_exists(img): issues.append('og-image')
    if not ANY_MARKER.search(src): issues.append('schema')
    return sorted(set(issues))

def main():
    state = load(STATE, {'version': 3, 'pages': {}})
    manifest = load(MANIFEST, {'version': 3, 'sector': 'special-needs-inclusive-education', 'pages': {}})
    state.setdefault('pages', {})
    manifest.setdefault('pages', {})

    files = []
    for scope in SCOPES:
        if scope.exists():
            files.extend(scope.rglob('*.html'))
    files = sorted(set(files))

    raw = {}
    title_counts, desc_counts = Counter(), Counter()
    read_failures = []
    for p in files:
        try:
            s = p.read_text(encoding='utf-8')
        except Exception as exc:
            read_failures.append({'path': rel(p), 'reason': f'read:{exc}'})
            continue
        raw[p] = s
        if get_title(s): title_counts[norm(get_title(s)).casefold()] += 1
        if meta(s, 'name', 'description'): desc_counts[norm(meta(s, 'name', 'description')).casefold()] += 1

    sm = sitemap_text()
    candidates = []
    skipped = defaultdict(int)
    failed = list(read_failures)

    for p, s in raw.items():
        path = rel(p)
        current = sha(s)
        prev = state['pages'].get(path, {})
        if prev.get('post_sha256') == current:
            skipped['unchanged'] += 1
            continue
        expected_can = canonical_for(p)
        if sm and expected_can not in sm:
            skipped['not-in-sitemap'] += 1
            continue
        issues = material_issues(s, p, title_counts, desc_counts)
        if 'blocked-existing-noindex' in issues:
            failed.append({'path': path, 'reason': 'existing-noindex-not-touched'})
            continue
        if 'blocked-external-canonical' in issues:
            failed.append({'path': path, 'reason': 'external-canonical-review-required'})
            continue
        if not issues:
            skipped['already-optimal'] += 1
            continue
        candidates.append((len(issues), path, p, issues))

    candidates.sort(key=lambda x: (-x[0], x[1]))
    changed = []
    totals = Counter()

    for _, path, p, issues in candidates:
        if len(changed) >= TARGET:
            break
        old = raw[p]
        t = norm(get_title(old)).casefold()
        d = norm(meta(old, 'name', 'description')).casefold()
        new, changes, err = enhance(old, p, title_counts[t] > 1 if t else False, desc_counts[d] > 1 if d else False)
        if err:
            failed.append({'path': path, 'reason': err})
            continue
        if new == old or not changes:
            skipped['no-op'] += 1
            continue
        ok, err = verify(new, p)
        if not ok:
            failed.append({'path': path, 'reason': err or 'validation-failed'})
            continue
        intent, queries = semantic_queries(new, path)
        if len(queries) < 500:
            failed.append({'path': path, 'reason': f'semantic-map-{len(queries)}'})
            continue
        if body_hash(new) != body_hash(old):
            failed.append({'path': path, 'reason': 'visible-body-integrity'})
            continue

        p.write_text(new, encoding='utf-8')
        post = sha(new)
        vf = body_hash(new)
        can = link(new, 'canonical')
        state['pages'][path] = {
            'pre_sha256': sha(old), 'post_sha256': post, 'visible_body_sha256': vf,
            'optimized_at': NOW, 'canonical': can, 'version': 'technical-seo-v3'
        }
        manifest['pages'][path] = {
            'canonical': can, 'primary_intent': intent, 'query_count': 500, 'queries': queries,
            'source_body_fingerprint': vf, 'updated_at': NOW
        }
        changed.append({'path': path, 'canonical': can, 'issues_before': issues, 'changes': changes})
        totals.update(changes)

    state.update({'version': 3, 'last_run_at': NOW, 'last_success_count': len(changed)})
    manifest.update({'version': 3, 'updated_at': NOW, 'minimum_queries_per_page': 500})
    save(STATE, state)
    save(MANIFEST, manifest)

    final_titles, final_descs, intents = Counter(), Counter(), Counter()
    for p in files:
        try:
            s = p.read_text(encoding='utf-8')
        except Exception:
            continue
        if get_title(s): final_titles[norm(get_title(s)).casefold()] += 1
        if meta(s, 'name', 'description'): final_descs[norm(meta(s, 'name', 'description')).casefold()] += 1
        item = manifest['pages'].get(rel(p))
        if item: intents[norm(item['primary_intent']).casefold()] += 1

    remaining = max(0, len(candidates) - len(changed))
    report = {
        'sector': 'ذوو الاحتياجات الخاصة والتربية الدامجة',
        'scope': ['/special-needs/', '/inclusive-education/'],
        'run_at': NOW,
        'target': TARGET,
        'success': len(changed),
        'status': 'complete' if len(changed) >= TARGET else 'incomplete',
        'scope_html_pages': len(raw),
        'candidate_pages': len(candidates),
        'eligible_remaining': remaining,
        'skipped_noop': sum(skipped.values()),
        'skipped_breakdown': dict(skipped),
        'failed': len(failed),
        'failures': failed[:200],
        'change_totals': dict(totals),
        'changed_pages': changed,
        'verification': {
            'visible_body_unchanged': True,
            'json_ld_validated': True,
            'canonical_self_checked': True,
            'og_twitter_consistency_checked': True,
            'robots_indexability_checked': True,
            'locale_lang_checked': True,
            'sitemap_checked': bool(sm),
            'semantic_queries_per_success': 500,
            'duplicate_title_groups': sum(v > 1 for v in final_titles.values()),
            'duplicate_description_groups': sum(v > 1 for v in final_descs.values()),
            'exact_primary_intent_overlap_groups': sum(v > 1 for v in intents.values()),
        },
    }
    save(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
