#!/usr/bin/env python3
"""Resilient live-demand adapter for the care-guides technical SEO agent.

The base engine owns page mutation and verification. This adapter only replaces
query evidence collection. Generated seeds are discovery inputs and never count.
A phrase counts only when a public autocomplete source returns it and it passes
page-specific condition/intent relevance checks.
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
    'adhd': ['adhd', 'attention deficit hyperactivity disorder', 'اضطراب فرط الحركة وتشتت الانتباه', 'فرط الحركة وتشتت الانتباه'],
    'autism': ['autism', 'autism spectrum disorder', 'asd', 'التوحد', 'اضطراب طيف التوحد'],
    'anxiety': ['anxiety', 'anxiety disorder', 'القلق', 'اضطراب القلق'],
    'depression': ['depression', 'depressive disorder', 'الاكتئاب'],
    'bipolar': ['bipolar disorder', 'bipolar', 'الاضطراب ثنائي القطب'],
    'ocd': ['ocd', 'obsessive compulsive disorder', 'الوسواس القهري'],
    'ptsd': ['ptsd', 'post traumatic stress disorder', 'اضطراب ما بعد الصدمة'],
    'panic': ['panic attacks', 'panic disorder', 'نوبات الهلع', 'اضطراب الهلع'],
    'schizophrenia': ['schizophrenia', 'الفصام'],
    'social-anxiety': ['social anxiety', 'social anxiety disorder', 'القلق الاجتماعي'],
    'eating': ['eating disorders', 'eating disorder', 'anorexia', 'bulimia', 'binge eating', 'اضطرابات الأكل', 'فقدان الشهية العصبي', 'النهام العصبي'],
}

INTENTS = {
    'assessment': ['assessment', 'evaluation', 'تقييم'],
    'diagnosis': ['diagnosis', 'diagnostic', 'تشخيص'],
    'differential': ['differential', 'differential diagnosis', 'التشخيص التفريقي'],
    'screening': ['screening', 'screen', 'فحص', 'تحري'],
    'treatment': ['treatment', 'therapy', 'علاج'],
    'care': ['care', 'care options', 'خيارات الرعاية', 'رعاية'],
    'family': ['family', 'caregiver', 'للأسرة', 'الأسرة'],
    'adult': ['adult', 'adults', 'للبالغين', 'البالغين'],
    'child': ['child', 'children', 'pediatric', 'للأطفال', 'الأطفال'],
    'workplace': ['workplace', 'work', 'العمل'],
    'school': ['school', 'education', 'المدرسة'],
    'rating': ['rating', 'rating scale', 'مقياس'],
    'scale': ['scale', 'score', 'مقياس', 'درجة'],
    'measurement': ['measurement', 'measure', 'قياس'],
    'reliability': ['reliability', 'reliable', 'الموثوقية', 'الثبات'],
    'validity': ['validity', 'valid', 'الصدق', 'الصلاحية'],
    'sensitivity': ['sensitivity', 'الحساسية'],
    'specificity': ['specificity', 'النوعية'],
    'cutoff': ['cutoff', 'cut off', 'threshold', 'الدرجة الفاصلة', 'عتبة'],
    'error': ['measurement error', 'error', 'خطأ القياس'],
    'evidence': ['evidence', 'research', 'الدليل العلمي', 'الأدلة'],
    'questions': ['questions', 'question', 'أسئلة', 'سؤال'],
    'appointment': ['appointment', 'visit', 'موعد التقييم', 'موعد'],
    'function': ['functioning', 'function', 'الأداء الوظيفي', 'الأداء'],
    'understand': ['understand', 'understanding', 'فهم'],
    'preparation': ['preparation', 'prepare', 'التحضير', 'استعداد'],
    'options': ['options', 'choices', 'خيارات'],
}

GENERIC = base.STOP | {'disorder', 'اضطراب', 'guide', 'دليل', 'health', 'mental', 'الصحة', 'النفسية', 'clinical', 'سريري', 'care', 'رعاية'}


def _tokens(text):
    return {z.casefold() for z in re.findall(r'[A-Za-z]{2,}|[\u0600-\u06FF]{2,}', text or '') if z.casefold() not in GENERIC and len(z) >= 3}


def _request_json(url):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; RawafidSEO/4.1; +https://healthrenewal.org/)',
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
            if str(k).lower() in {'k', 'key', 'phrase', 'text', 'query'} and isinstance(v, str):
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
    seen, rows = set(), []
    for x in out:
        k = x.casefold()
        if k != seed and k not in seen:
            seen.add(k)
            rows.append(x)
    return rows


def page_profile(s, p):
    rel = base.rp(p).lower()
    visible_name = (base.h1(s) + ' ' + base.core(s)).lower()
    matched_conditions = []
    for key, values in CONDITIONS.items():
        english_values = [v for v in values if re.search(r'[A-Za-z]', v)]
        if key in rel or any(v.lower() in visible_name for v in english_values):
            matched_conditions.extend(values)
    matched_intents = []
    for key, values in INTENTS.items():
        if key in rel:
            matched_intents.extend(values)
    core_tokens = _tokens(base.h1(s) + ' ' + base.core(s) + ' ' + p.parent.name.replace('-', ' '))
    condition_tokens = _tokens(' '.join(matched_conditions))
    intent_tokens = _tokens(' '.join(matched_intents))
    return {
        'conditions': matched_conditions,
        'intents': matched_intents,
        'core_tokens': core_tokens,
        'condition_tokens': condition_tokens,
        'intent_tokens': intent_tokens,
    }


def phrase_relevant(q, profile):
    toks = _tokens(q)
    if not toks:
        return False
    cond = profile['condition_tokens']
    intent = profile['intent_tokens']
    core = profile['core_tokens']
    if cond and not (toks & cond):
        return False
    if intent and not (toks & intent):
        return False
    overlap = toks & core
    if cond and intent:
        return bool(overlap) or bool((toks & cond) and (toks & intent))
    if cond:
        return bool(toks & cond) and (bool(overlap) or len(toks) >= 2)
    if intent:
        non_intent_core = core - intent
        return bool(toks & intent) and (not non_intent_core or bool(toks & non_intent_core))
    needed = 1 if len(core) <= 2 else 2
    return len(overlap) >= needed


def smart_seeds(s, p):
    seeds = list(base.seeds(s, p))
    profile = page_profile(s, p)
    concepts = profile['conditions'] or [base.core(s), p.parent.name.replace('-', ' ')]
    intents = profile['intents'] or ['guide', 'دليل']
    generated = []
    for concept in concepts[:8]:
        latin = bool(re.search(r'[A-Za-z]', concept)) and not re.search(r'[\u0600-\u06FF]', concept)
        letters = base.EN_LET if latin else base.AR_LET
        generated.append(concept)
        for intent in intents[:10]:
            same_script = (bool(re.search(r'[A-Za-z]', intent)) and latin) or (bool(re.search(r'[\u0600-\u06FF]', intent)) and not latin)
            if not same_script:
                continue
            generated.extend([f'{concept} {intent}', f'{intent} {concept}'])
            generated.extend(f'{concept} {intent} {c}' for c in letters)
            generated.extend(f'{intent} {concept} {c}' for c in letters[:16])
        generated.extend(f'{concept} {c}' for c in letters)
    seen = {base.norm(x).casefold() for x in seeds}
    for x in generated:
        x = base.norm(x)
        k = x.casefold()
        if x and k not in seen:
            seen.add(k)
            seeds.append(x)
        if len(seeds) >= 360:
            break
    return seeds


def collect(s, p):
    seeds = smart_seeds(s, p)
    profile = page_profile(s, p)
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
                if not phrase_relevant(q, profile):
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
        'policy': 'Only phrases returned by live public search-autocomplete endpoints count. Generated exploration seeds never count. For condition-specific pages, phrases must match the condition; for intent-specific pages they must also match the page intent.',
        'queried_seed_count': len(seeds),
        'sources': ['Bing Autocomplete', 'Yahoo Autocomplete', 'DuckDuckGo Autocomplete'],
        'source_returned_rows': dict(returned),
        'errors': dict(errors),
        'real_relevant_suggestion_count': len(rows),
        'relevance_profile': {
            'conditions': profile['conditions'],
            'intents': profile['intents'],
            'core_tokens': sorted(profile['core_tokens']),
        },
        'brand_combinations_not_counted': [base.core(s) + ' ' + base.SHORT, base.core(s) + ' ' + base.EN],
    }
    return rows[:base.MINQ], evidence


base.collect = collect
raise SystemExit(base.main())
