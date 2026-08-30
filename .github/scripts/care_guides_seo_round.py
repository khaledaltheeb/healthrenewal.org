#!/usr/bin/env python3
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import hashlib, html, json, re, statistics

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / 'care-guides'
SITEMAP = ROOT / 'sitemap.xml'
TARGET = 50
SITE = 'https://healthrenewal.org/'
BRAND = 'منصة روافد'
SHORT = 'روافد'
EN = 'Health Renewal'
IMAGE = SITE + 'assets/brand/rawafid-social-card.jpg'
STATE = ROOT / '.github/seo/care-guides-seo-state.json'
MANIFEST = ROOT / '.github/seo/care-guides-semantic-manifest.json'
REPORT = ROOT / '.github/reports/seo-care-guides-latest.json'
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
MINQ = 500
MAXSEED = 180
WORKERS = 32
TIMEOUT = 4
AR_HINT = ['ما هو', 'كيف', 'دليل', 'تقييم', 'تشخيص', 'علاج', 'أعراض', 'اسباب', 'أسباب', 'الفرق بين', 'للأطفال', 'للبالغين', 'للأسرة', 'أسئلة', 'متى', 'لماذا']
EN_HINT = ['what is', 'how to', 'guide', 'assessment', 'diagnosis', 'treatment', 'symptoms', 'causes', 'screening', 'children', 'adults', 'family', 'questions', 'when', 'why']
AR_LET = list('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')
EN_LET = list('abcdefghijklmnopqrstuvwxyz')
STOP = {'من', 'في', 'على', 'إلى', 'الى', 'عن', 'مع', 'ما', 'هو', 'هي', 'كيف', 'دليل', 'the', 'and', 'for', 'with', 'what', 'how', 'guide', 'of', 'to', 'a', 'an'}
MARK = 'rawafid:care-guides-seo:v3'


def norm(x):
    return re.sub(r'\s+', ' ', x or '').strip()


def hsh(x):
    return hashlib.sha256(x.encode()).hexdigest()


def rp(p):
    return p.relative_to(ROOT).as_posix()


def load(p, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return default


def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def vis(x):
    x = re.sub(r'<(?:script|style|noscript)\b[^>]*>.*?</(?:script|style|noscript)>', ' ', x, flags=re.I | re.S)
    return norm(html.unescape(re.sub(r'<[^>]+>', ' ', x)))


def attrs(tag):
    return {m.group(1).lower(): html.unescape(m.group(3)) for m in re.finditer(r'([:\w-]+)\s*=\s*([\"\'])(.*?)\2', tag, re.S)}


def title(s):
    m = re.search(r'<title\b[^>]*>(.*?)</title>', s, re.I | re.S)
    return vis(m.group(1)) if m else ''


def h1(s):
    m = re.search(r'<h1\b[^>]*>(.*?)</h1>', s, re.I | re.S)
    return vis(m.group(1)) if m else ''


def meta(s, key, name):
    for m in re.finditer(r'<meta\b[^>]*>', s, re.I | re.S):
        a = attrs(m.group())
        if a.get(key, '').lower() == name.lower():
            return norm(a.get('content', ''))
    return ''


def link(s, rel):
    for m in re.finditer(r'<link\b[^>]*>', s, re.I | re.S):
        a = attrs(m.group())
        if rel.lower() in a.get('rel', '').lower().split():
            return norm(a.get('href', ''))
    return ''


def body(s):
    m = re.search(r'<body\b', s, re.I)
    return s[m.start():] if m else ''


def bh(s):
    return hsh(body(s))


def page_url(p):
    x = rp(p)
    if x.endswith('index.html'):
        x = x[:-len('index.html')]
    return SITE + x.lstrip('/')


def core(s):
    t = title(s) or h1(s) or 'دليل رعاية'
    t = re.sub(r'\s*[|｜-]\s*(?:منصة\s+)?روافد.*$', '', t, flags=re.I)
    t = re.sub(r'\s*[|｜-]\s*Health\s+Renewal.*$', '', t, flags=re.I)
    return norm(t)


def trim(x, n=158):
    x = norm(x)
    if len(x) <= n:
        return x
    y = x[:n - 1]
    if ' ' in y:
        y = y.rsplit(' ', 1)[0]
    return y.rstrip('،؛:.-') + '…'


def desc_from(s):
    main = re.search(r'<main\b[^>]*>(.*?)</main>', body(s), re.I | re.S)
    scope = main.group(1) if main else body(s)
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>', scope, re.I | re.S):
        t = vis(m.group(1))
        if 80 <= len(t) <= 600:
            return trim(t)
    return trim(h1(s) or core(s))


def jsonld(s):
    types = set()
    for i, m in enumerate(re.finditer(r'<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>', s, re.I | re.S), 1):
        try:
            d = json.loads(html.unescape(m.group(1)).strip())
        except Exception as e:
            return False, f'json-ld-{i}:{e}', types
        queue = [d]
        while queue:
            x = queue.pop()
            if isinstance(x, dict):
                t = x.get('@type')
                if isinstance(t, str):
                    types.add(t)
                elif isinstance(t, list):
                    types.update(str(v) for v in t)
                queue.extend(x.values())
            elif isinstance(x, list):
                queue.extend(x)
    return True, '', types


def sitemap_urls(text=None):
    if text is None:
        try:
            text = SITEMAP.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            text = ''
    return {html.unescape(norm(m.group(1))).rstrip('/') for m in re.finditer(r'<loc>\s*(.*?)\s*</loc>', text, re.I | re.S)}


def add_sitemap_urls(text, urls):
    existing = sitemap_urls(text)
    additions = [u.rstrip('/') for u in urls if u.rstrip('/') not in existing]
    if not additions:
        return text, []
    block = ''.join(f'  <url>\n    <loc>{html.escape(u + "/")}</loc>\n  </url>\n' for u in additions)
    m = re.search(r'</urlset\s*>', text, re.I)
    if not m:
        raise ValueError('root-sitemap-is-not-urlset')
    return text[:m.start()] + block + text[m.start():], additions


def indexable(s):
    r = meta(s, 'name', 'robots').lower()
    return 'noindex' not in r and 'nofollow' not in r


def goodcan(x, expected):
    try:
        u = urlparse(x)
        return u.scheme in ('http', 'https') and u.netloc == 'healthrenewal.org' and x.rstrip('/') == expected.rstrip('/')
    except Exception:
        return False


def replace_attr(tag, name, value):
    esc = html.escape(value, quote=True)
    if re.search(r'\b' + re.escape(name) + r'\s*=', tag, re.I):
        return re.sub(r'(\b' + re.escape(name) + r'\s*=\s*)([\"\'])(.*?)\2', lambda m: m.group(1) + m.group(2) + esc + m.group(2), tag, count=1, flags=re.I | re.S)
    return tag[:-1] + f' {name}="{esc}">'


def insert_head(s, x):
    m = re.search(r'</head\s*>', s, re.I)
    return s[:m.start()] + x + '\n' + s[m.start():] if m else s


def set_title(s, value):
    tag = '<title>' + html.escape(value) + '</title>'
    m = re.search(r'<title\b[^>]*>.*?</title>', s, re.I | re.S)
    if not m:
        return insert_head(s, tag), True
    if m.group() == tag:
        return s, False
    return s[:m.start()] + tag + s[m.end():], True


def set_meta(s, key, name, value, replace=False):
    for m in re.finditer(r'<meta\b[^>]*>', s, re.I | re.S):
        a = attrs(m.group())
        if a.get(key, '').lower() == name.lower():
            if not replace:
                return s, False
            new = replace_attr(m.group(), 'content', value)
            return s[:m.start()] + new + s[m.end():], new != m.group()
    return insert_head(s, f'<meta {key}="{html.escape(name, quote=True)}" content="{html.escape(value, quote=True)}">'), True


def set_can(s, value):
    for m in re.finditer(r'<link\b[^>]*>', s, re.I | re.S):
        if 'canonical' in attrs(m.group()).get('rel', '').lower().split():
            new = replace_attr(m.group(), 'href', value)
            return s[:m.start()] + new + s[m.end():], new != m.group()
    return insert_head(s, f'<link rel="canonical" href="{html.escape(value, quote=True)}">'), True


def set_lang(s):
    m = re.search(r'<html\b[^>]*>', s, re.I | re.S)
    if not m:
        return s, False
    if attrs(m.group()).get('lang', '').lower().startswith('ar'):
        return s, False
    new = replace_attr(m.group(), 'lang', 'ar')
    return s[:m.start()] + new + s[m.end():], new != m.group()


def core_title(t):
    t = re.sub(r'\s*[|｜-]\s*Health\s+Renewal.*$', '', t, flags=re.I)
    return norm(re.sub(r'\s*[|｜-]\s*(?:منصة\s+)?روافد.*$', '', t, flags=re.I))


def schema_block(can, t, d, types):
    graph = []
    if 'Organization' not in types:
        graph.append({'@type': 'Organization', '@id': SITE + '#organization', 'name': BRAND, 'alternateName': EN, 'url': SITE})
    if 'WebSite' not in types:
        graph.append({'@type': 'WebSite', '@id': SITE + '#website', 'name': BRAND, 'alternateName': EN, 'url': SITE, 'inLanguage': 'ar'})
    if not ({'WebPage', 'MedicalWebPage', 'Article'} & types):
        graph.append({'@type': 'WebPage', '@id': can + '#webpage', 'url': can, 'name': t, 'description': d, 'inLanguage': 'ar'})
    if 'BreadcrumbList' not in types:
        parts = can.replace(SITE, '').strip('/').split('/')
        items = [{'@type': 'ListItem', 'position': 1, 'name': 'الرئيسية', 'item': SITE}]
        cur = SITE
        names = {'care-guides': 'أدلة الرعاية', 'clinical-literacy': 'الفهم السريري', 'aac': 'التواصل المعزز والبديل'}
        for i, x in enumerate(parts[:-1], 2):
            cur += x + '/'
            items.append({'@type': 'ListItem', 'position': i, 'name': names.get(x, x.replace('-', ' ')), 'item': cur})
        items.append({'@type': 'ListItem', 'position': len(items) + 1, 'name': core_title(t), 'item': can})
        graph.append({'@type': 'BreadcrumbList', '@id': can + '#breadcrumb', 'itemListElement': items})
    if not graph:
        return ''
    return f'<!-- {MARK} -->\n<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':')) + f'</script>\n<!-- /{MARK} -->'


def defects(s, p, sm, tc, dc):
    out = []
    t = title(s)
    d = meta(s, 'name', 'description')
    can = page_url(p)
    if not t or tc[t] > 1 or (SHORT not in t and EN.lower() not in t.lower()):
        out.append('title')
    if not d or dc[d] > 1 or len(d) < 70:
        out.append('description')
    if not goodcan(link(s, 'canonical'), can):
        out.append('canonical')
    if not meta(s, 'name', 'robots'):
        out.append('robots')
    if can.rstrip('/') not in sm:
        out.append('sitemap')
    required = [('property', 'og:type'), ('property', 'og:locale'), ('property', 'og:site_name'), ('property', 'og:title'), ('property', 'og:description'), ('property', 'og:url'), ('property', 'og:image'), ('name', 'twitter:card'), ('name', 'twitter:title'), ('name', 'twitter:description'), ('name', 'twitter:image')]
    if any(not meta(s, k, n) for k, n in required):
        out.append('social')
    ok, _, types = jsonld(s)
    if not ok:
        out.append('invalid-jsonld')
    elif 'Organization' not in types or 'WebSite' not in types or 'BreadcrumbList' not in types or not ({'WebPage', 'MedicalWebPage', 'Article'} & types):
        out.append('schema')
    m = re.search(r'<html\b[^>]*>', s, re.I | re.S)
    if not m or not attrs(m.group()).get('lang', '').lower().startswith('ar'):
        out.append('lang')
    return sorted(set(out))


def enhance(s, p, tc, dc):
    old_body = body(s)
    changes = []
    can = page_url(p)
    t = title(s)
    nt = t if t and (SHORT in t or EN.lower() in t.lower()) else core(s) + ' | ' + BRAND
    if not t or tc[t] > 1 or nt != t:
        s, changed = set_title(s, nt)
        if changed:
            changes.append('title')
    d = meta(s, 'name', 'description')
    if not d or dc[d] > 1 or len(d) < 70:
        nd = desc_from(s)
        if len(nd) >= 40:
            s, changed = set_meta(s, 'name', 'description', nd, True)
            if changed:
                changes.append('description')
            d = nd
    if not goodcan(link(s, 'canonical'), can):
        s, changed = set_can(s, can)
        if changed:
            changes.append('canonical')
    robots = meta(s, 'name', 'robots')
    if not robots:
        s, changed = set_meta(s, 'name', 'robots', 'index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1')
        if changed:
            changes.append('robots')
    elif 'noindex' not in robots.lower() and 'max-image-preview' not in robots.lower():
        s, changed = set_meta(s, 'name', 'robots', robots + ',max-image-preview:large', True)
        if changed:
            changes.append('robots')
    s, changed = set_lang(s)
    if changed:
        changes.append('lang')
    d = meta(s, 'name', 'description') or desc_from(s)
    t = title(s)
    socials = [
        ('property', 'og:type', 'article'), ('property', 'og:locale', 'ar_AR'), ('property', 'og:site_name', BRAND),
        ('property', 'og:title', t), ('property', 'og:description', d), ('property', 'og:url', can),
        ('property', 'og:image', IMAGE), ('property', 'og:image:alt', core(s)),
        ('name', 'twitter:card', 'summary_large_image'), ('name', 'twitter:title', t), ('name', 'twitter:description', d),
        ('name', 'twitter:image', IMAGE), ('name', 'twitter:image:alt', core(s))
    ]
    social_changed = False
    replace_names = {'og:locale', 'og:site_name', 'og:title', 'og:description', 'og:url', 'twitter:title', 'twitter:description'}
    for k, n, v in socials:
        current = meta(s, k, n)
        if not current or (n in replace_names and current != v):
            s, changed = set_meta(s, k, n, v, bool(current))
            social_changed |= changed
    if social_changed:
        changes.append('og-twitter')
    ok, err, types = jsonld(s)
    if not ok:
        return s, changes, err
    block = schema_block(can, t, d, types)
    if block:
        m = re.search(r'<!-- ' + re.escape(MARK) + r' -->.*?<!-- /' + re.escape(MARK) + r' -->', s, re.S)
        s = s[:m.start()] + block + s[m.end():] if m else insert_head(s, block)
        changes.append('schema')
    if body(s) != old_body:
        return s, changes, 'visible-body-changed'
    ok, err, _ = jsonld(s)
    return s, sorted(set(changes)), '' if ok else err


def topics(s, p):
    raw = [h1(s), core(s), p.parent.name.replace('-', ' ')]
    for m in re.finditer(r'<h[2-3]\b[^>]*>(.*?)</h[2-3]>', body(s), re.I | re.S):
        raw.append(vis(m.group(1)))
    out = []
    seen = set()
    for x in raw:
        x = norm(x)
        k = x.casefold()
        if x and k not in seen:
            seen.add(k)
            out.append(' '.join(x.split()[:10]))
    return out[:8]


def anchors(s, p):
    out = set()
    for x in topics(s, p):
        for z in re.findall(r'[A-Za-z]{2,}|[\u0600-\u06FF]{2,}', x):
            if z.casefold() not in STOP and len(z) >= 3:
                out.add(z.casefold())
    return out


def seeds(s, p):
    ts = topics(s, p)
    per_topic = []
    for t in ts[:6]:
        latin = bool(re.search(r'[A-Za-z]', t)) and not re.search(r'[\u0600-\u06FF]', t)
        hints = EN_HINT if latin else AR_HINT
        letters = EN_LET if latin else AR_LET
        candidates = [t]
        candidates += [f'{h} {t}' for h in hints]
        candidates += [f'{t} {c}' for c in letters]
        candidates += [f'{c} {t}' for c in letters[:12]]
        per_topic.append(candidates)
    out = []
    seen = set()
    i = 0
    while len(out) < MAXSEED and per_topic:
        alive = False
        for arr in per_topic:
            if i < len(arr):
                alive = True
                x = norm(arr[i])
                k = x.casefold()
                if x and k not in seen:
                    seen.add(k)
                    out.append(x)
                    if len(out) >= MAXSEED:
                        break
        if not alive:
            break
        i += 1
    return out


def google(q, hl='ar'):
    req = Request('https://suggestqueries.google.com/complete/search?client=firefox&hl=' + hl + '&q=' + quote(q), headers={'User-Agent': 'Mozilla/5.0 RawafidSEO/3.0'})
    with urlopen(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read().decode('utf-8', 'replace'))
    return [norm(str(x)) for x in data[1]] if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) else []


def ddg(q):
    req = Request('https://duckduckgo.com/ac/?q=' + quote(q) + '&type=list', headers={'User-Agent': 'Mozilla/5.0 RawafidSEO/3.0'})
    with urlopen(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read().decode('utf-8', 'replace'))
    return [norm(str(x.get('phrase', ''))) for x in data if isinstance(x, dict) and norm(str(x.get('phrase', '')))] if isinstance(data, list) else []


def related(q, anchor_set):
    toks = {z.casefold() for z in re.findall(r'[A-Za-z]{2,}|[\u0600-\u06FF]{2,}', q)}
    return bool(toks & anchor_set)


def collect(s, p):
    ss = seeds(s, p)
    anchor_set = anchors(s, p)
    found = {}
    errors = Counter()
    source_hits = Counter()
    future_meta = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for seed in ss:
            latin = bool(re.search(r'[A-Za-z]', seed)) and not re.search(r'[\u0600-\u06FF]', seed)
            future_meta[ex.submit(google, seed, 'en' if latin else 'ar')] = ('google_autocomplete', seed)
            future_meta[ex.submit(ddg, seed)] = ('duckduckgo_autocomplete', seed)
        for future in as_completed(future_meta):
            source, seed = future_meta[future]
            try:
                vals = future.result()
            except Exception as e:
                errors[source + ':' + type(e).__name__] += 1
                continue
            source_hits[source] += len(vals)
            for q in vals:
                if not related(q, anchor_set):
                    continue
                key = q.casefold()
                row = found.setdefault(key, {'phrase': q, 'sources': [], 'evidence_seeds': []})
                if source not in row['sources']:
                    row['sources'].append(source)
                if seed not in row['evidence_seeds'] and len(row['evidence_seeds']) < 3:
                    row['evidence_seeds'].append(seed)
    rows = list(found.values())
    rows.sort(key=lambda x: (len(x['sources']), len(x['phrase']), x['phrase']), reverse=True)
    evidence = {
        'captured_at': NOW,
        'policy': 'Only phrases returned by live public autocomplete endpoints count. Generated seeds never count. Results are filtered for topical overlap.',
        'queried_seed_count': len(ss),
        'sources': ['Google Autocomplete', 'DuckDuckGo Autocomplete'],
        'source_returned_rows': dict(source_hits),
        'errors': dict(errors),
        'real_relevant_suggestion_count': len(rows),
        'brand_combinations_not_counted': [core(s) + ' ' + SHORT, core(s) + ' ' + EN]
    }
    return rows[:MINQ], evidence


def checks(s, p, sm, q):
    t = title(s)
    d = meta(s, 'name', 'description')
    can = page_url(p)
    ok, _, types = jsonld(s)
    return {
        'title_present': bool(t),
        'description_present': len(d) >= 40,
        'canonical_exact': goodcan(link(s, 'canonical'), can),
        'indexable': indexable(s),
        'sitemap_included': can.rstrip('/') in sm,
        'jsonld_valid': ok,
        'schema_supported': bool({'WebPage', 'MedicalWebPage', 'Article'} & types) and 'BreadcrumbList' in types,
        'og_consistent': meta(s, 'property', 'og:title') == t and meta(s, 'property', 'og:description') == d and meta(s, 'property', 'og:url').rstrip('/') == can.rstrip('/') and bool(meta(s, 'property', 'og:image')),
        'twitter_consistent': meta(s, 'name', 'twitter:title') == t and meta(s, 'name', 'twitter:description') == d and bool(meta(s, 'name', 'twitter:image')),
        'locale_ar': meta(s, 'property', 'og:locale') == 'ar_AR',
        'real_query_count': len(q) >= MINQ
    }


def fingerprint(s, q):
    payload = {
        'title': title(s), 'description': meta(s, 'name', 'description'), 'canonical': link(s, 'canonical'),
        'robots': meta(s, 'name', 'robots'), 'og': meta(s, 'property', 'og:title'), 'twitter': meta(s, 'name', 'twitter:title'),
        'queries': hsh('\n'.join(x['phrase'] for x in q))
    }
    return hsh(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main():
    if not SCOPE.exists() or not SITEMAP.exists():
        return 2
    pages = sorted(p for p in SCOPE.rglob('index.html') if p.parent != SCOPE)
    original_sitemap = SITEMAP.read_text(encoding='utf-8', errors='ignore')
    sm = sitemap_urls(original_sitemap)
    docs = {}
    title_counts = Counter()
    desc_counts = Counter()
    for p in pages:
        try:
            s = p.read_text(encoding='utf-8')
        except Exception:
            continue
        docs[p] = s
        if title(s):
            title_counts[title(s)] += 1
        if meta(s, 'name', 'description'):
            desc_counts[meta(s, 'name', 'description')] += 1

    state = load(STATE, {'version': 3, 'pages': {}})
    manifest = load(MANIFEST, {'version': 3, 'source_policy': 'live-autocomplete-only', 'pages': {}})
    successes, skipped, failed = [], [], []
    source_errors = Counter()
    candidates = []

    for p, s in docs.items():
        ds = defects(s, p, sm, title_counts, desc_counts)
        if not indexable(s):
            skipped.append({'path': rp(p), 'reason': 'existing-noindex-or-nofollow'})
            continue
        if not ds:
            skipped.append({'path': rp(p), 'reason': 'no-material-seo-defect'})
            continue
        if 'invalid-jsonld' in ds:
            failed.append({'path': rp(p), 'reason': 'existing-invalid-jsonld'})
            continue
        candidates.append((len(ds), rp(p), p, s, ds))

    candidates.sort(key=lambda x: (-x[0], x[1]))
    intents = set()
    query_sets = []
    suggestion_counts = []
    planned_sitemap = []

    for _, _, p, s, ds in candidates:
        if len(successes) >= TARGET:
            break
        intent = norm(h1(s) or core(s)).casefold()
        if not intent or intent in intents:
            skipped.append({'path': rp(p), 'reason': 'duplicate-primary-intent'})
            continue
        q, evidence = collect(s, p)
        count = evidence['real_relevant_suggestion_count']
        suggestion_counts.append(count)
        source_errors.update(evidence['errors'])
        if len(q) < MINQ:
            skipped.append({'path': rp(p), 'reason': 'insufficient-live-demand-evidence', 'real_suggestions': count, 'queried_seed_count': evidence['queried_seed_count']})
            continue
        qs = {x['phrase'].casefold() for x in q}
        if any(len(qs & z) / max(1, len(qs | z)) >= 0.65 for z in query_sets):
            skipped.append({'path': rp(p), 'reason': 'query-cannibalization-risk'})
            continue

        old_body_hash = bh(s)
        ns, changes, err = enhance(s, p, title_counts, desc_counts)
        if err:
            failed.append({'path': rp(p), 'reason': err})
            continue
        can = page_url(p)
        sitemap_missing = can.rstrip('/') not in sm
        material_changes = sorted(set(changes + (['sitemap'] if sitemap_missing else [])))
        if not material_changes:
            skipped.append({'path': rp(p), 'reason': 'no-op-after-analysis'})
            continue
        if bh(ns) != old_body_hash:
            failed.append({'path': rp(p), 'reason': 'body-hash-changed'})
            continue

        simulated_sm = set(sm)
        simulated_sm.add(can.rstrip('/'))
        ck = checks(ns, p, simulated_sm, q)
        ck['visible_body_unchanged'] = bh(ns) == old_body_hash
        if not all(ck.values()):
            failed.append({'path': rp(p), 'reason': 'verification-failed', 'checks': ck})
            continue

        if ns != s:
            p.write_text(ns, encoding='utf-8')
            reread = p.read_text(encoding='utf-8')
            if reread != ns or bh(reread) != old_body_hash:
                p.write_text(s, encoding='utf-8')
                failed.append({'path': rp(p), 'reason': 'save-verification-failed'})
                continue

        fp = fingerprint(ns, q)
        manifest['pages'][rp(p)] = {
            'canonical': can, 'primary_intent': h1(s) or core(s), 'fingerprint': fp, 'updated_at': NOW,
            'real_search_phrases': q, 'evidence': evidence,
            'brand_combinations': [core(s) + ' ' + SHORT, core(s) + ' ' + EN]
        }
        state['pages'][rp(p)] = {'fingerprint': fp, 'body_hash': old_body_hash, 'last_success_at': NOW, 'changes': material_changes}
        successes.append({'path': rp(p), 'canonical': can, 'changes': material_changes, 'real_search_phrases': len(q), 'checks': ck})
        if sitemap_missing:
            planned_sitemap.append(can)
        intents.add(intent)
        query_sets.append(qs)

    final_title_counts = Counter()
    final_desc_counts = Counter()
    for p in pages:
        try:
            s = p.read_text(encoding='utf-8')
        except Exception:
            continue
        if title(s):
            final_title_counts[title(s)] += 1
        if meta(s, 'name', 'description'):
            final_desc_counts[meta(s, 'name', 'description')] += 1
    keep = []
    duplicate_paths = []
    for item in successes:
        p = ROOT / item['path']
        s = p.read_text(encoding='utf-8')
        if final_title_counts[title(s)] > 1 or final_desc_counts[meta(s, 'name', 'description')] > 1:
            if p in docs:
                p.write_text(docs[p], encoding='utf-8')
            duplicate_paths.append(item['path'])
            failed.append({'path': item['path'], 'reason': 'post-round-title-or-description-duplicate'})
            state['pages'].pop(item['path'], None)
            manifest['pages'].pop(item['path'], None)
        else:
            keep.append(item)
    successes = keep

    surviving = {x['canonical'].rstrip('/') for x in successes}
    sitemap_targets = [u for u in planned_sitemap if u.rstrip('/') in surviving]
    sitemap_text, sitemap_added = add_sitemap_urls(original_sitemap, sitemap_targets)
    if sitemap_added:
        SITEMAP.write_text(sitemap_text, encoding='utf-8')
    final_sm = sitemap_urls(SITEMAP.read_text(encoding='utf-8', errors='ignore'))

    final_successes = []
    for item in successes:
        p = ROOT / item['path']
        s = p.read_text(encoding='utf-8')
        q = manifest['pages'][item['path']]['real_search_phrases']
        ck = checks(s, p, final_sm, q)
        ck['visible_body_unchanged'] = bh(s) == state['pages'][item['path']]['body_hash']
        item['checks'] = ck
        if all(ck.values()):
            final_successes.append(item)
        else:
            failed.append({'path': item['path'], 'reason': 'final-saved-state-verification-failed', 'checks': ck})
            if p in docs:
                p.write_text(docs[p], encoding='utf-8')
            state['pages'].pop(item['path'], None)
            manifest['pages'].pop(item['path'], None)
    successes = final_successes

    final_surviving = {x['canonical'].rstrip('/') for x in successes}
    if set(u.rstrip('/') for u in sitemap_added) - final_surviving:
        sitemap_text, _ = add_sitemap_urls(original_sitemap, [u for u in sitemap_targets if u.rstrip('/') in final_surviving])
        SITEMAP.write_text(sitemap_text, encoding='utf-8')

    reason_counts = Counter(x['reason'] for x in skipped)
    failure_counts = Counter(x['reason'] for x in failed)
    complete = len(successes) >= TARGET
    stats = {
        'tested_pages_for_live_demand': len(suggestion_counts),
        'max_real_relevant_suggestions': max(suggestion_counts, default=0),
        'median_real_relevant_suggestions': statistics.median(suggestion_counts) if suggestion_counts else 0,
        'min_real_relevant_suggestions': min(suggestion_counts, default=0)
    }
    report = {
        'round': 'care-guides-technical-seo', 'generated_at': NOW, 'target': TARGET,
        'success': len(successes), 'skipped_noop_or_ineligible': len(skipped), 'failed': len(failed),
        'eligible_candidates_before_round': len(candidates), 'eligible_remaining_estimate': max(0, len(candidates) - len(successes)),
        'complete': complete, 'successes': successes, 'skipped': skipped, 'failures': failed,
        'skip_reason_counts': dict(reason_counts), 'failure_reason_counts': dict(failure_counts),
        'source_failures': dict(source_errors), 'demand_diagnostics': stats,
        'sitemap_added_urls': len([u for u in sitemap_added if u.rstrip('/') in final_surviving]),
        'verification': {
            'visible_body_unchanged': all(x['checks']['visible_body_unchanged'] for x in successes) if successes else True,
            'json_ld_validated': all(x['checks']['jsonld_valid'] for x in successes) if successes else True,
            'semantic_queries_per_success': min((x['real_search_phrases'] for x in successes), default=0),
            'autocomplete_only_counting': True, 'generated_seeds_count_toward_500': False,
            'topical_filter_applied': True, 'sitemap_required_for_success': True,
            'noindex_pages_modified': False, 'title_description_unique_for_successes': not duplicate_paths
        },
        'blocker': None if complete else 'Fewer than 50 care-guide pages passed the live autocomplete-demand and final technical verification gates.'
    }
    state['updated_at'] = NOW
    manifest['updated_at'] = NOW
    save(STATE, state)
    save(MANIFEST, manifest)
    save(REPORT, report)
    print(json.dumps({
        'success': len(successes), 'skipped': len(skipped), 'failed': len(failed), 'complete': complete,
        'candidates': len(candidates), 'skip_reason_counts': dict(reason_counts),
        'failure_reason_counts': dict(failure_counts), 'demand_diagnostics': stats,
        'sitemap_added_urls': report['sitemap_added_urls'], 'source_failures': dict(source_errors)
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
