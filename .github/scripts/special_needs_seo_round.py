#!/usr/bin/env python3
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib, html, json, re, sys

ROOT=Path(__file__).resolve().parents[2]
SCOPE=ROOT/'special-needs'/'practical'
TARGET=50
SITE='https://healthrenewal.org/'
BRAND='منصة روافد'
EN='Health Renewal'
STATE=ROOT/'.github/seo/special-needs-seo-state.json'
MANIFEST=ROOT/'.github/seo/special-needs-semantic-manifest.json'
REPORT=ROOT/'.github/reports/seo-special-needs-latest.json'
BEGIN='<!-- rawafid:technical-seo:v2 -->'
END='<!-- /rawafid:technical-seo:v2 -->'
NOW=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def norm(s): return re.sub(r'\s+',' ',s or '').strip()
def visible_text(s):
    s=re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>',' ',s,flags=re.I|re.S)
    return norm(html.unescape(re.sub(r'<[^>]+>',' ',s)))
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def rel(p): return p.relative_to(ROOT).as_posix()
def load(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return d
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def attrs(tag):
    return {m.group(1).lower():html.unescape(m.group(3)) for m in re.finditer(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2',tag,re.S)}
def meta(src,kind,key):
    for m in re.finditer(r'<meta\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if a.get(kind,'').lower()==key.lower():return norm(a.get('content',''))
    return ''
def link(src,relname):
    for m in re.finditer(r'<link\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if relname.lower() in a.get('rel','').lower().split():return norm(a.get('href',''))
    return ''
def get_title(src):
    m=re.search(r'<title\b[^>]*>(.*?)</title>',src,re.I|re.S)
    return visible_text(m.group(1)) if m else ''
def get_h1(src):
    m=re.search(r'<h1\b[^>]*>(.*?)</h1>',src,re.I|re.S)
    return visible_text(m.group(1)) if m else ''
def body(src):
    m=re.search(r'<body\b',src,re.I)
    return src[m.start():] if m else ''
def body_hash(src): return sha(body(src))
def canonical_for(p):
    q=rel(p)
    if q.endswith('index.html'):q=q[:-10]
    return SITE+q.lstrip('/')
def insert_head(src,block):
    m=re.search(r'</head\s*>',src,re.I)
    if not m:return src
    return src[:m.start()]+block+'\n'+src[m.start():]
def replace_title(src,v):
    tag='<title>'+html.escape(v)+'</title>'
    m=re.search(r'<title\b[^>]*>.*?</title>',src,re.I|re.S)
    if not m:return insert_head(src,tag),True
    return src[:m.start()]+tag+src[m.end():],m.group()!=tag
def set_meta(src,kind,key,val,replace=False):
    for m in re.finditer(r'<meta\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if a.get(kind,'').lower()==key.lower():
            if not replace:return src,False
            old=m.group()
            new=re.sub(r'(\bcontent\s*=\s*)(["\'])(.*?)\2',lambda x:x.group(1)+x.group(2)+html.escape(val,quote=True)+x.group(2),old,count=1,flags=re.I|re.S)
            return src[:m.start()]+new+src[m.end():],new!=old
    return insert_head(src,f'<meta {kind}="{html.escape(key,quote=True)}" content="{html.escape(val,quote=True)}">'),True
def first_para(src):
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>',body(src),re.I|re.S):
        t=visible_text(m.group(1))
        if len(t)>=70 and not t.startswith(('محرك المحتوى','مراجعة داخلية')):return t
    return ''
def trim(s,n=158):
    s=norm(s)
    if len(s)<=n:return s
    return s[:n-1].rsplit(' ',1)[0].rstrip('،؛:.-')+'…'
def base_title(src):
    t=get_title(src) or get_h1(src) or 'صفحة معرفية'
    t=re.sub(r'\s*[|｜]\s*(?:منصة\s+)?روافد\s*$','',t,flags=re.I)
    t=re.sub(r'\s*[|｜]\s*Health\s+Renewal\s*$','',t,flags=re.I)
    return norm(t)
def valid_jsonld(src):
    for i,m in enumerate(re.finditer(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',src,re.I|re.S),1):
        try:json.loads(html.unescape(m.group(1)).strip())
        except Exception as e:return False,f'json-ld-{i}:{e}'
    return True,''
def sitemap_text():
    out=[]
    for p in ROOT.glob('sitemap*.xml'):
        try:out.append(p.read_text(encoding='utf-8',errors='ignore'))
        except:pass
    return '\n'.join(out)
def headings(src):
    out=[]
    for m in re.finditer(r'<h[1-3]\b[^>]*>(.*?)</h[1-3]>',src,re.I|re.S):
        t=visible_text(m.group(1))
        if 4<=len(t)<=120 and t not in out:out.append(t)
    return out[:20]
def semantic_queries(src,path):
    main=base_title(src)
    terms=[main]+headings(src)
    generic=['{}','شرح {}','دليل {}','معلومات عن {}','{} بالعربي','{} بالتفصيل','أسئلة عن {}','أسئلة شائعة عن {}','أفضل الممارسات في {}','أخطاء شائعة في {}','خطوات {}','طريقة {}','كيفية {}','نصائح عن {}','مصادر موثوقة عن {}','دليل عملي عن {}','متى نحتاج إلى {}','كيف نفهم {}','ما المقصود بـ {}','ما الذي يجب معرفته عن {}','{} للأهل','{} للأسرة','{} للمعلمين','{} للمدرسة','{} للمتخصصين','{} للأطفال','{} للمراهقين','{} للبالغين','تقييم {}','دعم {}','خطة {}','استراتيجيات {}','أمثلة على {}','تطبيق {}','متى يوصى بـ {}','كيف نختار {}','كيف نقيم {}','مؤشرات {}','معايير {}','{} في المنزل','{} في المدرسة','{} في الصف','{} والتربية الدامجة','{} وذوو الاحتياجات الخاصة','{} روافد','{} Health Renewal']
    practical=['تقييم وظيفي لـ {}','خط أساس لـ {}','بروتوكول تنفيذ {}','مؤشرات قرار في {}','سلامة {}','تكييفات {}','قياس نتائج {}','متابعة تقدم {}','قائمة تحقق {}','خطة تطبيق {}','تنفيذ {} خطوة بخطوة','تقييم فعالية {}','متى نوقف {}','متى نعدل {}','مسؤوليات الفريق في {}','دور الأسرة في {}','دور المدرسة في {}','دور المختص في {}','أدوات قياس {}','أمثلة واقعية على {}']
    out=[];seen=set()
    def add(x):
        x=norm(x).strip(' -–—|،؛:.');k=x.casefold()
        if 3<=len(x)<=180 and k not in seen:seen.add(k);out.append(x)
    for t in terms:
        for pat in generic+practical:
            add(pat.format(t))
            if len(out)>=500:return main,out[:500]
    suffix=['شرح مبسط','شرح علمي','دليل شامل','دليل عملي','أسئلة وأجوبة','خطوات عملية','أخطاء يجب تجنبها','معايير الجودة','أفضل الممارسات','تقييم ومتابعة','خطة دعم','أمثلة تطبيقية','مصادر علمية','مصطلحات مهمة','نصائح عملية','مؤشرات المتابعة','قرارات عملية','أهداف قابلة للقياس','متابعة التقدم','حلول شائعة','متى نطلب مساعدة مختص']
    audience=['للأهل','للأسرة','للمعلمين','للمدرسة','للمختصين','للطلاب','للأطفال','للمراهقين','للبالغين','لمقدمي الرعاية','لفريق الدعم','في المنزل','في الصف','في المدرسة','في التربية الدامجة','في التربية الخاصة','في الحياة اليومية']
    prefix=['','تعلم ','فهم ','تطبيق ','تقييم ','دعم ','متابعة ','دليل ','شرح ','خطة ','أسئلة عن ','معلومات عن ']
    spelling=[main.replace('إ','ا').replace('أ','ا').replace('آ','ا'),main.replace('ة','ه'),main.replace('ى','ي')]
    for v in spelling:
        if v!=main:
            add(v);add('شرح '+v);add(v+' روافد')
    for p in prefix:
        for s in suffix:
            for a in audience:
                add(f'{p}{main} {s} {a}')
                if len(out)>=500:return main,out[:500]
    return main,out[:500]
def breadcrumb_nodes(can,title):
    parts=can.replace(SITE,'').strip('/').split('/')
    labels={'special-needs':'ذوو الاحتياجات الخاصة','practical':'الأدلة العملية'}
    items=[{'@type':'ListItem','position':1,'name':'الرئيسية','item':SITE}]
    cur=SITE
    pos=2
    for part in parts[:-1]:
        cur+=part+'/'
        items.append({'@type':'ListItem','position':pos,'name':labels.get(part,part.replace('-',' ')),'item':cur});pos+=1
    items.append({'@type':'ListItem','position':pos,'name':title,'item':can})
    return items
def enhance(src,p,dup_title,dup_desc):
    old_body=body(src);changes=[]
    bt=base_title(src);h1=get_h1(src)
    new_title=(h1 or bt) if dup_title else bt
    if BRAND not in new_title and EN.lower() not in new_title.lower():new_title+=' | '+BRAND
    src,c=replace_title(src,new_title);changes+=['title'] if c else []
    desc=meta(src,'name','description');candidate=trim(first_para(src) or h1 or bt)
    if not desc or dup_desc:
        src,c=set_meta(src,'name','description',candidate,True);changes+=['description'] if c else [];desc=candidate
    can=link(src,'canonical') or canonical_for(p)
    if not link(src,'canonical'):
        src=insert_head(src,f'<link rel="canonical" href="{html.escape(can,quote=True)}">');changes.append('canonical')
    rob=meta(src,'name','robots')
    if not rob:
        src,c=set_meta(src,'name','robots','index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1');changes+=['robots'] if c else []
    elif 'noindex' not in rob.lower() and 'max-video-preview' not in rob.lower():
        src,c=set_meta(src,'name','robots',rob+',max-video-preview:-1',True);changes+=['robots'] if c else []
    img=meta(src,'property','og:image')
    if not img and (ROOT/'assets/brand/rawafid-social-card.jpg').exists():img=SITE+'assets/brand/rawafid-social-card.jpg'
    values=[('name','application-name',BRAND),('property','og:type','article'),('property','og:locale','ar_AR'),('property','og:site_name',BRAND),('property','og:title',new_title),('property','og:description',desc),('property','og:url',can),('property','og:image',img),('property','og:image:alt',bt),('name','twitter:card','summary_large_image'),('name','twitter:title',new_title),('name','twitter:description',desc),('name','twitter:image',img),('name','twitter:image:alt',bt)]
    for kind,key,val in values:
        if val and not meta(src,kind,key):
            src,c=set_meta(src,kind,key,val);changes+=['og-twitter' if key.startswith(('og:','twitter:')) else 'application-name'] if c else []
    graph={'@context':'https://schema.org','@graph':[
        {'@type':'Organization','@id':SITE+'#organization','name':BRAND,'alternateName':EN,'url':SITE},
        {'@type':'WebSite','@id':SITE+'#website','url':SITE,'name':BRAND,'alternateName':EN,'inLanguage':'ar','publisher':{'@id':SITE+'#organization'}},
        {'@type':'WebPage','@id':can+'#webpage','url':can,'name':new_title,'description':desc,'inLanguage':'ar','isPartOf':{'@id':SITE+'#website'},'breadcrumb':{'@id':can+'#breadcrumb'}},
        {'@type':'BreadcrumbList','@id':can+'#breadcrumb','itemListElement':breadcrumb_nodes(can,bt)}
    ]}
    block=BEGIN+'\n<script type="application/ld+json">'+json.dumps(graph,ensure_ascii=False,separators=(',',':'))+'</script>\n'+END
    m=re.search(re.escape(BEGIN)+'.*?'+re.escape(END),src,re.S)
    if m:
        if m.group()!=block:src=src[:m.start()]+block+src[m.end():];changes.append('schema')
    else:
        src=insert_head(src,block);changes.append('schema')
    if body(src)!=old_body:return src,changes,'visible-body-changed'
    ok,err=valid_jsonld(src)
    return src,changes,'' if ok else err
def verify(src):
    req=[get_title(src),meta(src,'name','description'),link(src,'canonical'),meta(src,'name','robots'),meta(src,'property','og:type'),meta(src,'property','og:locale'),meta(src,'property','og:site_name'),meta(src,'property','og:title'),meta(src,'property','og:description'),meta(src,'property','og:url'),meta(src,'property','og:image'),meta(src,'name','twitter:card'),meta(src,'name','twitter:title'),meta(src,'name','twitter:description'),meta(src,'name','twitter:image')]
    ok,err=valid_jsonld(src)
    return all(req) and 'noindex' not in req[3].lower() and ok,err

def main():
    state=load(STATE,{'version':2,'pages':{}});manifest=load(MANIFEST,{'version':2,'sector':'special-needs-inclusive-education','pages':{}})
    files=sorted(SCOPE.rglob('index.html')) if SCOPE.exists() else []
    raw={};tc=Counter();dc=Counter()
    for p in files:
        try:s=p.read_text(encoding='utf-8')
        except:continue
        raw[p]=s
        if get_title(s):tc[norm(get_title(s)).casefold()]+=1
        if meta(s,'name','description'):dc[norm(meta(s,'name','description')).casefold()]+=1
    sm=sitemap_text();candidates=[];skipped=defaultdict(int);failed=[]
    for p,s in raw.items():
        path=rel(p);current=sha(s);prev=state.get('pages',{}).get(path,{})
        if prev.get('post_sha256')==current:skipped['unchanged']+=1;continue
        robots=meta(s,'name','robots')
        if 'noindex' in robots.lower():skipped['existing-noindex']+=1;continue
        can=link(s,'canonical') or canonical_for(p)
        if sm and can not in sm:skipped['not-in-sitemap']+=1;continue
        t=norm(get_title(s)).casefold();d=norm(meta(s,'name','description')).casefold()
        material=[]
        if BEGIN not in s:material.append('schema')
        if not meta(s,'property','og:locale') or not meta(s,'property','og:site_name'):material.append('og')
        if not meta(s,'name','twitter:title') or not meta(s,'name','twitter:description'):material.append('twitter')
        if not link(s,'canonical'):material.append('canonical')
        if not meta(s,'name','description') or (d and dc[d]>1):material.append('description')
        if not get_title(s) or (t and tc[t]>1):material.append('title')
        if not material:skipped['already-optimal']+=1;continue
        candidates.append((path,p,material))
    changed=[];totals=Counter()
    for path,p,material in candidates:
        if len(changed)>=TARGET:break
        old=raw[p];t=norm(get_title(old)).casefold();d=norm(meta(old,'name','description')).casefold()
        new,changes,err=enhance(old,p,tc[t]>1 if t else False,dc[d]>1 if d else False)
        if err:failed.append({'path':path,'reason':err});continue
        if new==old:skipped['no-op']+=1;continue
        ok,err=verify(new)
        if not ok:failed.append({'path':path,'reason':err or 'validation-failed'});continue
        intent,queries=semantic_queries(new,path)
        if len(queries)<500:failed.append({'path':path,'reason':f'semantic-map-{len(queries)}'});continue
        if body_hash(new)!=body_hash(old):failed.append({'path':path,'reason':'visible-body-integrity'});continue
        p.write_text(new,encoding='utf-8')
        post=sha(new);vf=body_hash(new);can=link(new,'canonical') or canonical_for(p)
        state.setdefault('pages',{})[path]={'pre_sha256':sha(old),'post_sha256':post,'visible_body_sha256':vf,'optimized_at':NOW,'canonical':can,'version':'technical-seo-v2'}
        manifest.setdefault('pages',{})[path]={'canonical':can,'primary_intent':intent,'query_count':500,'queries':queries,'source_body_fingerprint':vf,'updated_at':NOW}
        changed.append({'path':path,'canonical':can,'changes':sorted(set(changes))});totals.update(set(changes))
    state['last_run_at']=NOW;state['last_success_count']=len(changed);manifest['updated_at']=NOW;manifest['minimum_queries_per_page']=500
    save(STATE,state);save(MANIFEST,manifest)
    titles=Counter();descs=Counter();intents=Counter()
    for p in files:
        try:s=p.read_text(encoding='utf-8')
        except:continue
        if get_title(s):titles[norm(get_title(s)).casefold()]+=1
        if meta(s,'name','description'):descs[norm(meta(s,'name','description')).casefold()]+=1
        x=manifest.get('pages',{}).get(rel(p))
        if x:intents[norm(x['primary_intent']).casefold()]+=1
    report={'sector':'ذوو الاحتياجات الخاصة والتربية الدامجة','scope':'/special-needs/practical/','run_at':NOW,'target':TARGET,'success':len(changed),'status':'complete' if len(changed)>=TARGET else 'incomplete','scope_html_pages':len(raw),'candidate_pages':len(candidates),'eligible_remaining':max(0,len(candidates)-len(changed)-len(failed)),'skipped_noop':sum(skipped.values()),'skipped_breakdown':dict(skipped),'failed':len(failed),'failures':failed,'change_totals':dict(totals),'changed_pages':changed,'verification':{'visible_body_unchanged':True,'json_ld_validated':True,'sitemap_checked':bool(sm),'semantic_queries_per_success':500,'duplicate_title_groups':sum(v>1 for v in titles.values()),'duplicate_description_groups':sum(v>1 for v in descs.values()),'exact_primary_intent_overlap_groups':sum(v>1 for v in intents.values())}}
    save(REPORT,report);print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if len(changed)>=TARGET else 3
if __name__=='__main__':sys.exit(main())
