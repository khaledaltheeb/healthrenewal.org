from __future__ import annotations
import hashlib, json, re, sys
from collections import defaultdict
from pathlib import Path

SITE=Path(sys.argv[1] if len(sys.argv)>1 else '_site')
OUT=SITE/'api'/'all-labs-v22.json'
AR_DIAC=re.compile(r'[\u064b-\u065f\u0670]')
EXPECTED_ASSESSMENTS=40
EXPECTED_COGNITIVE=53
EXPECTED_LAB_HTML=95
LAB_RUNTIME_VERSION='213'
TITLE_TYPOS=('المتقدمةة','الأساسيةة')


def norm(v:object)->str:
    s=AR_DIAC.sub('',str(v or '').lower())
    s=s.replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ى','ي').replace('ة','ه')
    return re.sub(r'[^\w\u0600-\u06ff]+',' ',s).strip()


def adjacent_repeated_phrase(v:object)->str:
    tokens=' '.join(str(v or '').split()).split(' ')
    for size in range(min(4,len(tokens)//2),0,-1):
        for index in range(0,len(tokens)-size*2+1):
            if tokens[index:index+size]==tokens[index+size:index+size*2]:
                return ' '.join(tokens[index:index+size])
    return ''


def definition(path:Path)->dict:
    text=path.read_text(encoding='utf-8')
    m=re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>',text,re.S)
    if not m: raise ValueError('missing lab-definition')
    return json.loads(m.group(1))


def audit_runtime_cache(errors:list[str])->dict:
    pages=[]
    for root_name in ('assessment-lab','cognitive-lab'):
        root=SITE/root_name
        pages.extend(sorted(root.rglob('*.html')))
    pages=sorted(set(pages))
    if len(pages)!=EXPECTED_LAB_HTML:
        errors.append(f'lab HTML count {len(pages)} != {EXPECTED_LAB_HTML}')
    versioned_marker=f'assets/js/lab-v12.js?v={LAB_RUNTIME_VERSION}'
    versioned=0
    for page in pages:
        rel=page.relative_to(SITE).as_posix()
        text=page.read_text(encoding='utf-8')
        count=text.count(versioned_marker)
        if count!=1:
            errors.append(f'{rel}: versioned lab runtime count {count} != 1')
        if re.search(r'assets/js/lab-v12\.js(?:["\'])',text):
            errors.append(f'{rel}: unversioned lab runtime remains')
        versioned+=int(count==1)
    return {'pages':len(pages),'versioned_pages':versioned,'runtime_version':int(LAB_RUNTIME_VERSION),'unversioned_pages':0}


def main()->None:
    errors=[]; warnings=[]; rows=[]
    groups={'assessment':sorted((SITE/'assessment-lab').glob('*/index.html')),'cognitive':sorted((SITE/'cognitive-lab').glob('*/index.html'))}
    if len(groups['assessment'])!=EXPECTED_ASSESSMENTS: errors.append(f"assessment count {len(groups['assessment'])} != {EXPECTED_ASSESSMENTS}")
    if len(groups['cognitive'])!=EXPECTED_COGNITIVE: errors.append(f"cognitive count {len(groups['cognitive'])} != {EXPECTED_COGNITIVE}")
    cache=audit_runtime_cache(errors)
    seen_slug={}; seen_title={}; signatures=defaultdict(list); question_signatures=defaultdict(list)
    for kind,pages in groups.items():
        for page in pages:
            rel=page.relative_to(SITE).as_posix()
            try: d=definition(page)
            except Exception as exc: errors.append(f'{rel}: {exc}'); continue
            slug=str(d.get('slug','')).strip(); title=str(d.get('title','')).strip(); category=str(d.get('category','')).strip(); mode=str(d.get('mode','')).strip()
            if not slug or not title: errors.append(f'{rel}: missing slug/title')
            if slug in seen_slug: errors.append(f'duplicate slug {slug}: {seen_slug[slug]} / {rel}')
            seen_slug[slug]=rel
            nt=norm(title)
            if nt in seen_title: errors.append(f'duplicate normalized title {title}: {seen_title[nt]} / {rel}')
            seen_title[nt]=rel
            if kind=='cognitive':
                repeated=adjacent_repeated_phrase(title)
                if repeated: errors.append(f'{rel}: repeated adjacent title phrase: {repeated}')
                for typo in TITLE_TYPOS:
                    if typo in title: errors.append(f'{rel}: malformed title token: {typo}')
            payload={k:v for k,v in d.items() if k not in {'slug','title','description'}}
            sig=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            signatures[(kind,sig)].append(rel)
            row={'kind':kind,'slug':slug,'title':title,'category':category,'mode':mode,'path':rel}
            if kind=='assessment':
                qs=d.get('questions'); opts=d.get('options')
                if not isinstance(qs,list) or len(qs)<3: errors.append(f'{rel}: fewer than 3 questions')
                if not isinstance(opts,list) and not all(isinstance(q,dict) and isinstance(q.get('options'),list) for q in (qs or [])): errors.append(f'{rel}: options missing')
                normalized_questions=[]
                for i,q in enumerate(qs or []):
                    text=q if isinstance(q,str) else q.get('text','') if isinstance(q,dict) else ''
                    nq=norm(text)
                    if len(nq)<8: errors.append(f'{rel}: question {i+1} too short')
                    normalized_questions.append(nq)
                    question_signatures[nq].append(f'{rel}#{i+1}')
                if len(normalized_questions)!=len(set(normalized_questions)): errors.append(f'{rel}: repeated questions inside assessment')
                if not d.get('score_type'): warnings.append(f'{rel}: no explicit score_type; generic interpretation only')
                row.update(questions=len(qs or []),score_type=d.get('score_type','generic'))
            else:
                stages=int(d.get('stages',5) or 0); trials=int(d.get('trials_per_stage',6) or 0)
                if stages<3: errors.append(f'{rel}: stages {stages} < 3')
                if trials<4: errors.append(f'{rel}: trials_per_stage {trials} < 4')
                if not (mode or category): errors.append(f'{rel}: no mode/category')
                row.update(stages=stages,trials_per_stage=trials,total_trials=stages*trials)
            rows.append(row)
    for (kind,sig),paths in signatures.items():
        if len(paths)>1: errors.append(f'probable duplicate {kind} definitions: {paths}')
    repeated_cross={q:locs for q,locs in question_signatures.items() if q and len(locs)>=3}
    for q,locs in list(repeated_cross.items())[:100]: warnings.append(f'repeated question text across assessments ({len(locs)}): {q[:90]} -> {locs[:6]}')
    report={'version':213,'assessment_count':len(groups['assessment']),'cognitive_count':len(groups['cognitive']),'expected_assessment_count':EXPECTED_ASSESSMENTS,'expected_cognitive_count':EXPECTED_COGNITIVE,'cognitive_title_phrase_guard':True,'lab_runtime_cache':cache,'tools':rows,'error_count':len(errors),'errors':errors,'warning_count':len(warnings),'warnings':warnings}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if errors: raise SystemExit('\n'.join(errors[:100]))
if __name__=='__main__': main()
