#!/usr/bin/env python3
"""Source adapter for the care-guides SEO agent.

Keeps the v3 page/metadata/sitemap verification engine intact while replacing
high-volume Google autocomplete harvesting with public Bing, Yahoo and
DuckDuckGo suggestion sources. Only source-returned phrases count.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from urllib.request import Request, urlopen
import html
import json
import re

import care_guides_seo_round as base

base.MAXSEED = 220
base.WORKERS = 24
base.TIMEOUT = 5

CONDITIONS = {
    'adhd': ['adhd', 'اضطراب فرط الحركة وتشتت الانتباه', 'فرط الحركة وتشتت الانتباه'],
    'autism': ['autism', 'autism spectrum disorder', 'التوحد', 'اضطراب طيف التوحد'],
    'anxiety': ['anxiety', 'anxiety disorder', 'القلق', 'اضطراب القلق'],
    'depression': ['depression', 'depressive disorder', 'الاكتئاب'],
    'bipolar': ['bipolar disorder', 'bipolar', 'الاضطراب ثنائي القطب'],
    'ocd': ['ocd', 'obsessive compulsive disorder', 'الوسواس القهري'],
    'ptsd': ['ptsd', 'post traumatic stress disorder', 'اضطراب ما بعد الصدمة'],
    'panic': ['panic attacks', 'panic disorder', 'نوبات الهلع', 'اضطراب الهلع'],
    'schizophrenia': ['schizophrenia', 'الفصام'],
    'social-anxiety': ['social anxiety', 'social anxiety disorder', 'القلق الاجتماعي'],
    'eating': ['eating disorders', 'eating disorder', 'اضطرابات الأكل'],
}

INTENTS = {
    'assessment': ['assessment', 'تقييم'],
    'diagnosis': ['diagnosis', 'تشخيص'],
    'differential': ['differential diagnosis', 'التشخيص التفريقي'],
    'screening': ['screening', 'فحص', 'تحري'],
    'treatment': ['treatment', 'علاج'],
    'care': ['care options', 'خيارات الرعاية'],
    'family': ['family', 'للأسرة'],
    'adult': ['adults', 'للبالغين'],
    'child': ['children', 'للأطفال'],
    'workplace': ['workplace', 'العمل'],
    'school': ['school', 'المدرسة'],
    'rating': ['rating scale', 'مقياس'],
    'scale': ['scale', 'مقياس'],
    'measurement': ['measurement', 'قياس'],
    'reliability': ['reliability', 'الموثوقية'],
    'validity': ['validity', 'الصدق', 'الصلاحية'],
    'sensitivity': ['sensitivity', 'الحساسية'],
    'specificity': ['specificity', 'النوعية'],
    'cutoff': ['cutoff score', 'الدرجة الفاصلة'],
    'error': ['measurement error', 'خطأ القياس'],
    'evidence': ['evidence', 'الدليل العلمي'],
    'questions': ['questions', 'أسئلة'],
    'appointment': ['appointment', 'موعد التقييم'],
    'function': ['functioning', 'الأداء الوظيفي'],
}


def _request_json(url):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; RawafidSEO/4.0; +https://healthrenewal.org/)',
        'Accept': 'application/json,text/plain,*/*',
    })
    with urlopen(req, timeout=base.TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def bing(q):
    latin = bool(re.search(r'[A-Za-z]', q)) and not re.search(r'[\u0600-\u06FF]', q)
    market = 'en-US' if latin else 'ar-SA'
    data = _request_json('https://api.bing.com/osjson.aspx?market=' + market + '&query=' + quote(q))
    if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
        return [base.norm(str(x)) for x in data[1] if base.norm(str(x))]
    return []


def _collect_strings(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            lk = str(k).lower()
            if lk in {'k', 'key', 'phrase', 'text', 'query'} and isinstance(v, str):
                x = base.norm(html.unescape(re.sub(r'<[^>]+>', ' ', v)))
                if x:
                    out.append(x)
            else:
                _collect_strings(v, out)
    elif isinstance(node, list):
        for x in node:
            _collect_strings(x, out)


def yahoo(q):
    data = _request_json('https://search.yahoo.com/sugg/gossip/gossip-us-ura/?output=sd1&nresults=20&command=' + quote(q))
    out = []
    _collect_strings(data, out)
    seed = base.norm(q).casefold()
    seen = set()
    rows = []
    for x in out:
        k = x.casefold()
        if k != seed and k not in seen:
            seen.add(k)
            rows.append(x)
    return rows


def smart_seeds(s, p):
    seeds = list(base.seeds(s, p))
    slug = p.parent.name.lower()
    rel = base.rp(p).lower()
    concepts = []
    for key, vals in CONDITIONS.items():
        if key in rel or any(v.lower() in (base.h1(s) + ' ' + base.core(s)).lower() for v in vals if re.search(r'[A-Za-z]', v)):
            concepts.extend(vals)
    intents = []
    for key, vals in INTENTS.items():
        if key in slug or key in rel:
            intents.extend(vals)
    if not concepts:
        concepts = [base.core(s), slug.replace('-', ' ')]
    if not intents:
        intents = ['guide', 'دليل']

    ar_letters = base.AR_LET
    en_letters = base.EN_LET
    generated = []
    for concept in concepts[:6]:
        latin = bool(re.search(r'[A-Za-z]', concept)) and not re.search(r'[\u0600-\u06FF]', concept)
        letters = en_letters if latin else ar_letters
        generated.append(concept)
        for intent in intents[:8]:
            same_script = (bool(re.search(r'[A-Za-z]', intent)) and latin) or (bool(re.search(r'[\u0600-\u06FF]', intent)) and not latin)
            if not same_script:
                continue
            generated.extend([f'{concept} {intent}', f'{intent} {concept}'])
            generated.extend(f'{concept} {intent} {c}' for c in letters)
        generated.extend(f'{concept} {c}' for c in letters)

    seen = {base.norm(x).casefold() for x in seeds}
    for x in generated:
        x = base.norm(x)
        k = x.casefold()
        if x and k not in seen:
            seen.add(k)
            seeds.append(x)
        if len(seeds) >= 320:
            break
    return seeds


def collect(s, p):
    seeds = smart_seeds(s, p)
    anchor_set = base.anchors(s, p)
    for seed in seeds:
        for tok in re.findall(r'[A-Za-z]{2,}|[\u0600-\u06FF]{2,}', seed):
            if tok.casefold() not in base.STOP and len(tok) >= 3:
                anchor_set.add(tok.casefold())

    found = {}
    errors = Counter()
    returned = Counter()
    future_meta = {}
    sources = [('bing_autocomplete', bing), ('yahoo_autocomplete', yahoo), ('duckduckgo_autocomplete', base.ddg)]
    with ThreadPoolExecutor(max_workers=base.WORKERS) as ex:
        for seed in seeds:
            for name, fn in sources:
                future_meta[ex.submit(fn, seed)] = (name, seed)
        for future in as_completed(future_meta):
            name, seed = future_meta[future]
            try:
                vals = future.result()
            except Exception as e:
                code = getattr(e, 'code', None)
                errors[f'{name}:{type(e).__name__}' + (f':{code}' if code is not None else '')] += 1
                continue
            returned[name] += len(vals)
            for q in vals:
                if not base.related(q, anchor_set):
                    continue
                key = q.casefold()
                row = found.setdefault(key, {'phrase': q, 'sources': [], 'evidence_seeds': []})
                if name not in row['sources']:
                    row['sources'].append(name)
                if seed not in row['evidence_seeds'] and len(row['evidence_seeds']) < 3:
                    row['evidence_seeds'].append(seed)

    rows = list(found.values())
    rows.sort(key=lambda x: (len(x['sources']), len(x['phrase']), x['phrase']), reverse=True)
    evidence = {
        'captured_at': base.NOW,
        'policy': 'Only phrases returned by live public search-autocomplete endpoints count. Generated exploration seeds never count. Results are filtered for topical overlap.',
        'queried_seed_count': len(seeds),
        'sources': ['Bing Autocomplete', 'Yahoo Autocomplete', 'DuckDuckGo Autocomplete'],
        'source_returned_rows': dict(returned),
        'errors': dict(errors),
        'real_relevant_suggestion_count': len(rows),
        'brand_combinations_not_counted': [base.core(s) + ' ' + base.SHORT, base.core(s) + ' ' + base.EN],
    }
    return rows[:base.MINQ], evidence


base.collect = collect
raise SystemExit(base.main())
