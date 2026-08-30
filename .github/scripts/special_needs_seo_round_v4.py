#!/usr/bin/env python3
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
import hashlib, html, json, re, sys

ROOT = Path(__file__).resolve().parents[2]
SCOPES = [ROOT / 'special-needs', ROOT / 'inclusive-education']
TARGET = 50
SITE = 'https://healthrenewal.org/'
BRAND = 'منصة روافد'
EN = 'Health Renewal'
SECTOR_SITEMAP = ROOT / 'sitemap-special-needs.xml'
SITEMAP_INDEX = ROOT / 'sitemap-index.xml'
STATE = ROOT / '.github/seo/special-needs-seo-state.json'
MANIFEST = ROOT / '.github/seo/special-needs-semantic-manifest.json'
REPORT = ROOT / '.github/reports/seo-special-needs-latest.json'
MARKER = '<!-- rawafid:technical-seo:v4 -->'
ENDMARK = '<!-- /rawafid:technical-seo:v4 -->'
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

AR_LABELS = {
    'special-needs':'ذوو الاحتياجات الخاصة','inclusive-education':'التربية الدامجة',
    'education':'التربية الخاصة والتعليم الدامج','conditions':'الحالات والمتلازمات',
    'practical':'الأدلة العملية','assistive-technology':'التقنيات المساندة',
    'communication':'التواصل','aac':'التواصل المعزز والبديل','hearing':'السمع',
    'learning':'التعلم','early-intervention':'التدخل المبكر','guides':'الأدلة',
    'evidence':'الأدلة العلمية','speech-language':'النطق واللغة','vision':'البصر'
}

def norm(s): return re.sub(r'\s+',' ',s or '').strip()
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def rel(p): return p.relative_to(ROOT).as_posix()
def load(p,d):
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return d
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def attrs(tag):
    return {m.group(1).lower():html.unescape(m.group(3)) for m in re.finditer(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2',tag,re.S)}
def visible(s):
    s=re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>',' ',s,flags=re.I|re.S)
    return norm(html.unescape(re.sub(r'<[^>]+>',' ',s)))
def body(src):
    m=re.search(r'<body\b',src,re.I); return src[m.start():] if m else ''
def body_sha(src): return sha(body(src))
def meta(src,kind,key):
    for m in re.finditer(r'<meta\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if a.get(kind,'').lower()==key.lower(): return norm(a.get('content',''))
    return ''
def title(src):
    m=re.search(r'<title\b[^>]*>(.*?)</title>',src,re.I|re.S); return visible(m.group(1)) if m else ''
def h1(src):
    m=re.search(r'<h1\b[^>]*>(.*?)</h1>',src,re.I|re.S); return visible(m.group(1)) if m else ''
def lang(src):
    m=re.search(r'<html\b[^>]*>',src,re.I|re.S); return attrs(m.group()).get('lang','') if m else ''
def canonical(src):
    for m in re.finditer(r'<link\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if 'canonical' in a.get('rel','').lower().split(): return norm(a.get('href',''))
    return ''
def expected_canonical(p):
    x=rel(p)
    if x.endswith('index.html'): x=x[:-10]
    elif x.endswith('.html'): x=x[:-5]+'/'
    return SITE+x.lstrip('/')
def insert_head(src,block):
    m=re.search(r'</head\s*>',src,re.I)
    return src[:m.start()]+block+'\n'+src[m.start():] if m else src
def set_title(src,v):
    tag='<title>'+html.escape(v)+'</title>'; m=re.search(r'<title\b[^>]*>.*?</title>',src,re.I|re.S)
    if not m:return insert_head(src,tag),True
    return src[:m.start()]+tag+src[m.end():],m.group()!=tag
def set_meta(src,kind,key,v):
    for m in re.finditer(r'<meta\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if a.get(kind,'').lower()==key.lower():
            old=m.group()
            if re.search(r'\bcontent\s*=',old,re.I):
                new=re.sub(r'(\bcontent\s*=\s*)(["\'])(.*?)\2',lambda x:x.group(1)+x.group(2)+html.escape(v,quote=True)+x.group(2),old,count=1,flags=re.I|re.S)
            else:new=old[:-1]+f' content="{html.escape(v,quote=True)}">'
            return src[:m.start()]+new+src[m.end():],new!=old
    return insert_head(src,f'<meta {kind}="{html.escape(key,quote=True)}" content="{html.escape(v,quote=True)}">'),True
def set_canonical(src,v):
    for m in re.finditer(r'<link\b[^>]*>',src,re.I|re.S):
        a=attrs(m.group())
        if 'canonical' in a.get('rel','').lower().split():
            old=m.group(); new=re.sub(r'(\bhref\s*=\s*)(["\'])(.*?)\2',lambda x:x.group(1)+x.group(2)+html.escape(v,quote=True)+x.group(2),old,count=1,flags=re.I|re.S)
            return src[:m.start()]+new+src[m.end():],new!=old
    return insert_head(src,f'<link rel="canonical" href="{html.escape(v,quote=True)}">'),True
def set_lang(src):
    m=re.search(r'<html\b[^>]*>',src,re.I|re.S)
    if not m:return src,False
    old=m.group()
    if re.search(r'\blang\s*=',old,re.I):new=re.sub(r'(\blang\s*=\s*)(["\'])(.*?)\2',r'\1\2ar\2',old,count=1,flags=re.I|re.S)
    else:new=old[:-1]+' lang="ar">'
    return src[:m.start()]+new+src[m.end():],new!=old
def first_para(src):
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>',body(src),re.I|re.S):
        t=visible(m.group(1))
        if len(t)>=70 and not t.startswith(('محرك المحتوى','مراجعة داخلية','تنبيه','ملاحظة')):return t
    return ''
def trim(s,n=158):
    s=norm(s)
    if len(s)<=n:return s
    return s[:n-1].rsplit(' ',1)[0].rstrip('،؛:.-')+'…'
def base_title(src):
    t=title(src) or h1(src) or 'صفحة معرفية'
    t=re.sub(r'\s*[|｜]\s*(?:منصة\s+)?روافد\s*$','',t,flags=re.I)
    t=re.sub(r'\s*[|｜]\s*Health\s+Renewal\s*$','',t,flags=re.I)
    return norm(t)
def parent_label(path):
    parts=Path(path).parts[:-1]
    labels=[AR_LABELS[p] for p in parts if p in AR_LABELS]
    return ' — '.join(labels[-2:]) if labels else 'المعرفة المتخصصة'
def local_image_ok(url):
    if not url:return False
    if not url.startswith(SITE):return True
    return (ROOT/url[len(SITE):].split('?',1)[0].lstrip('/')).is_file()
def valid_jsonld(src):
    found=0
    for i,m in enumerate(re.finditer(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',src,re.I|re.S),1):
        found+=1
        try:json.loads(html.unescape(m.group(1)).strip())
        except Exception as e:return False,f'json-ld-{i}:{e}'
    return found>0,'' if found else 'json-ld-missing'
def headings(src):
    out=[]
    for m in re.finditer(r'<h[1-3]\b[^>]*>(.*?)</h[1-3]>',src,re.I|re.S):
        t=visible(m.group(1))
        if 4<=len(t)<=120 and t not in out and not t.startswith(('المراجع','المصادر','المحتويات')):out.append(t)
    return out[:20]
def queries(src,path):
    main=base_title(src); label=parent_label(path); terms=[main]+headings(src)
    patterns=['{}','شرح {}','دليل {}','معلومات عن {}','{} بالعربي','{} بالتفصيل','أسئلة عن {}','أسئلة شائعة عن {}','أفضل الممارسات في {}','أخطاء شائعة في {}','خطوات {}','كيفية {}','نصائح عن {}','مصادر موثوقة عن {}','دليل عملي عن {}','متى نحتاج إلى {}','كيف نفهم {}','ما المقصود بـ {}','{} للأهل','{} للأسرة','{} للمعلمين','{} للمدرسة','{} للمتخصصين','{} للأطفال','{} للمراهقين','{} للبالغين','تقييم {}','دعم {}','خطة {}','استراتيجيات {}','أمثلة على {}','تطبيق {}','كيف نختار {}','كيف نقيم {}','مؤشرات {}','معايير {}','{} في المنزل','{} في المدرسة','{} في الصف','{} والتربية الدامجة','{} وذوو الاحتياجات الخاصة','{} روافد','{} Health Renewal']
    if '/conditions/' in '/'+path: extra=['أعراض {}','علامات {}','أسباب {}','تشخيص {}','التشخيص المبكر لـ {}','فحوصات {}','تأهيل {}','التدخل المبكر لـ {}','متابعة {}','التعايش مع {}','دعم الأسرة في {}','التعليم مع {}','مضاعفات {}']
    elif any(x in '/'+path for x in ('/education/','/inclusive-education/','/iep-')): extra=['{} في التعليم الدامج','{} في التربية الخاصة','تكييفات {}','تسهيلات {}','خطة فردية لـ {}','IEP و{}','UDL و{}','التصميم الشامل و{}','تقييم الطلاب في {}','استراتيجيات صفية لـ {}','دور المعلم في {}','قياس تقدم {}']
    elif any(x in '/'+path for x in ('/aac/','/communication/','/speech','/hearing/')): extra=['تقييم التواصل في {}','تدخلات التواصل في {}','AAC و{}','لغة وتواصل {}','تدريب الأسرة على {}','أهداف تواصل في {}','أنشطة منزلية لـ {}','اختيار وسيلة التواصل لـ {}','التقنية المساندة في {}']
    else: extra=['دعم الأسرة في {}','دعم المدرسة في {}','خطة عملية لـ {}','قائمة تحقق لـ {}','أسئلة المختص عن {}','قرارات يومية في {}','قياس نتائج {}','متابعة تقدم {}']
    out=[]; seen=set()
    def add(q):
        q=norm(q).strip(' -–—|،؛:.'); k=q.casefold()
        if 3<=len(q)<=180 and k not in seen: seen.add(k); out.append(q)
    for term in terms:
        for pat in patterns+extra:
            add(pat.format(term))
            if len(out)>=500:return f'{main} — {label}',out[:500]
    suffix=['شرح مبسط','شرح علمي','دليل شامل','دليل عملي','أسئلة وأجوبة','خطوات عملية','أخطاء يجب تجنبها','معايير الجودة','أفضل الممارسات','تقييم ومتابعة','خطة دعم','أمثلة تطبيقية','مصادر علمية','مصطلحات مهمة','نصائح عملية','مؤشرات المتابعة','قرارات عملية','أهداف قابلة للقياس','متابعة التقدم','حلول شائعة','متى نطلب مساعدة مختص']
    audience=['للأهل','للأسرة','للمعلمين','للمدرسة','للمختصين','للطلاب','للأطفال','للمراهقين','للبالغين','لمقدمي الرعاية','في المنزل','في الصف','في المدرسة','في التربية الدامجة','في التربية الخاصة','في الحياة اليومية']
    prefixes=['','تعلم ','فهم ','تطبيق ','تقييم ','دعم ','متابعة ','دليل ','شرح ','خطة ','أسئلة عن ','معلومات عن ']
    for pre in prefixes:
        for s in suffix:
            for a in audience:
                add(f'{pre}{main} {s} {a}')
                if len(out)>=500:return f'{main} — {label}',out[:500]
    return f'{main} — {label}',out[:500]
def breadcrumb(can,name,path):
    parts=list(Path(path).parts[:-1]); items=[{'@type':'ListItem','position':1,'name':'الرئيسية','item':SITE}]
    cur=SITE; pos=2
    for part in parts:
        cur+=part+'/'; items.append({'@type':'ListItem','position':pos,'name':AR_LABELS.get(part,part.replace('-',' ')),'item':cur}); pos+=1
    items.append({'@type':'ListItem','position':pos,'name':name,'item':can}); return items
def schema_block(can,name,desc,path):
    graph={'@context':'https://schema.org','@graph':[
        {'@type':'Organization','@id':SITE+'#organization','name':BRAND,'alternateName':EN,'url':SITE},
        {'@type':'WebSite','@id':SITE+'#website','url':SITE,'name':BRAND,'alternateName':EN,'inLanguage':'ar','publisher':{'@id':SITE+'#organization'}},
        {'@type':'WebPage','@id':can+'#webpage','url':can,'name':name,'description':desc,'inLanguage':'ar','isPartOf':{'@id':SITE+'#website'},'breadcrumb':{'@id':can+'#breadcrumb'}},
        {'@type':'BreadcrumbList','@id':can+'#breadcrumb','itemListElement':breadcrumb(can,base_title_from_name(name),path)}]}
    return MARKER+'\n<script type="application/ld+json">'+json.dumps(graph,ensure_ascii=False,separators=(',',':'))+'</script>\n'+ENDMARK
def base_title_from_name(name):
    return re.sub(r'\s*\|\s*(?:منصة\s+)?روافد\s*$','',name).strip()
def existing_locs(path):
    if not path.exists():return set()
    txt=path.read_text(encoding='utf-8',errors='ignore')
    return {html.unescape(x.strip()) for x in re.findall(r'<loc>(.*?)</loc>',txt,re.I|re.S)}
def append_sector_urls(urls):
    urls=sorted(set(urls)-existing_locs(SECTOR_SITEMAP))
    if not urls:return 0
    txt=SECTOR_SITEMAP.read_text(encoding='utf-8')
    block=''.join('\n  <url>\n    <loc>'+html.escape(u)+'</loc>\n  </url>' for u in urls)+'\n'
    if '</urlset>' not in txt: raise RuntimeError('sector-sitemap-invalid')
    txt=txt.replace('</urlset>',block+'</urlset>',1)
    ET.fromstring(txt)
    SECTOR_SITEMAP.write_text(txt,encoding='utf-8')
    return len(urls)
def ensure_sector_sitemap_registered():
    if not SITEMAP_INDEX.exists():return False
    loc=SITE+'sitemap-special-needs.xml'; txt=SITEMAP_INDEX.read_text(encoding='utf-8')
    if loc in txt:return False
    block=f'  <sitemap><loc>{loc}</loc></sitemap>\n'
    if '</sitemapindex>' not in txt: raise RuntimeError('sitemap-index-invalid')
    txt=txt.replace('</sitemapindex>',block+'</sitemapindex>',1)
    ET.fromstring(txt)
    SITEMAP_INDEX.write_text(txt,encoding='utf-8')
    return True

def enhance(src,p,dup_t,dup_d):
    old_body=body(src); changes=[]; path=rel(p); bt=base_title(src); current_title=title(src); can=expected_canonical(p)
    target_title=current_title or h1(src) or bt
    if dup_t: target_title=f'{h1(src) or bt} | {parent_label(path)} | {BRAND}'
    elif BRAND not in target_title and EN.lower() not in target_title.lower(): target_title=target_title.rstrip(' |')+' | '+BRAND
    if target_title!=current_title:
        src,c=set_title(src,target_title); changes+=['title'] if c else []
    desc=meta(src,'name','description'); target_desc=desc
    if not desc or dup_d:
        target_desc=trim(first_para(src) or h1(src) or bt)
        if dup_d and first_para(src): target_desc=trim((h1(src) or bt)+': '+first_para(src))
        src,c=set_meta(src,'name','description',target_desc); changes+=['description'] if c else []
    if canonical(src)!=can:
        if canonical(src) and not canonical(src).startswith(SITE):return src,changes,'external-canonical-review-required'
        src,c=set_canonical(src,can); changes+=['canonical'] if c else []
    robots=meta(src,'name','robots')
    if 'noindex' in robots.lower():return src,changes,'existing-noindex-not-touched'
    desired=['index','follow','max-snippet:-1','max-image-preview:large','max-video-preview:-1']
    if not robots: newrob=','.join(desired)
    else:
        newrob=robots; low=robots.lower()
        for item in desired:
            if item.split(':')[0] not in low:newrob+=(',' if newrob else '')+item
    if newrob!=robots:
        src,c=set_meta(src,'name','robots',newrob); changes+=['indexability'] if c else []
    if lang(src).lower() not in ('ar','ar-sa','ar-jo'):
        src,c=set_lang(src); changes+=['lang'] if c else []
    img=meta(src,'property','og:image'); fallback=SITE+'assets/brand/rawafid-social-card.jpg' if (ROOT/'assets/brand/rawafid-social-card.jpg').is_file() else ''
    if not local_image_ok(img):img=fallback
    ogtype='article' if re.search(r'<article\b|"@type"\s*:\s*"(?:Article|MedicalWebPage|TechArticle)"',src,re.I) else 'website'
    pairs=[('name','application-name',BRAND),('property','og:type',ogtype),('property','og:locale','ar_AR'),('property','og:site_name',BRAND),('property','og:title',target_title),('property','og:description',target_desc),('property','og:url',can),('name','twitter:card','summary_large_image' if img else 'summary'),('name','twitter:title',target_title),('name','twitter:description',target_desc)]
    if img:pairs += [('property','og:image',img),('property','og:image:alt',bt),('name','twitter:image',img),('name','twitter:image:alt',bt)]
    for kind,key,val in pairs:
        if val and meta(src,kind,key)!=val:
            src,c=set_meta(src,kind,key,val); changes+=['og-twitter' if key.startswith(('og:','twitter:')) else 'application-name'] if c else []
    block=schema_block(can,target_title,target_desc,path)
    m=re.search(re.escape(MARKER)+r'.*?'+re.escape(ENDMARK),src,re.S)
    if m:
        if m.group()!=block:src=src[:m.start()]+block+src[m.end():];changes.append('schema')
    else:src=insert_head(src,block);changes.append('schema')
    if body(src)!=old_body:return src,changes,'visible-body-changed'
    ok,err=valid_jsonld(src);return src,sorted(set(changes)),'' if ok else err

def verify(src,p):
    can=expected_canonical(p); rob=meta(src,'name','robots').lower()
    if 'noindex' in rob:return False,'noindex-present'
    if canonical(src)!=can:return False,'canonical-mismatch'
    if lang(src).lower() not in ('ar','ar-sa','ar-jo'):return False,'lang-mismatch'
    if meta(src,'property','og:url')!=can:return False,'og-url-mismatch'
    if meta(src,'property','og:title')!=title(src) or meta(src,'name','twitter:title')!=title(src):return False,'social-title-mismatch'
    if meta(src,'property','og:description')!=meta(src,'name','description') or meta(src,'name','twitter:description')!=meta(src,'name','description'):return False,'social-description-mismatch'
    if not all([title(src),meta(src,'name','description'),meta(src,'property','og:locale'),meta(src,'property','og:site_name'),meta(src,'name','twitter:card')]):return False,'required-metadata-missing'
    img=meta(src,'property','og:image')
    if img and not local_image_ok(img):return False,'og-image-missing'
    return valid_jsonld(src)

def main():
    state=load(STATE,{'version':4,'pages':{}});manifest=load(MANIFEST,{'version':4,'sector':'special-needs-inclusive-education','pages':{}})
    state.setdefault('pages',{});manifest.setdefault('pages',{})
    files=[]
    for scope in SCOPES:
        if scope.exists():files.extend(scope.rglob('*.html'))
    files=sorted(set(files)); raw={}; tc=Counter();dc=Counter();failed=[]
    for p in files:
        try:s=p.read_text(encoding='utf-8')
        except Exception as e:failed.append({'path':rel(p),'reason':f'read:{e}'});continue
        raw[p]=s
        if title(s):tc[norm(title(s)).casefold()]+=1
        if meta(s,'name','description'):dc[norm(meta(s,'name','description')).casefold()]+=1
    sector_locs=existing_locs(SECTOR_SITEMAP); candidates=[]; skipped=defaultdict(int)
    for p,s in raw.items():
        path=rel(p); oldstate=state['pages'].get(path,{})
        if oldstate.get('post_sha256')==sha(s):skipped['unchanged']+=1;continue
        robots=meta(s,'name','robots').lower()
        if 'noindex' in robots:failed.append({'path':path,'reason':'existing-noindex-not-touched'});continue
        can=expected_canonical(p); curcan=canonical(s)
        if curcan and curcan!=can and not curcan.startswith(SITE):failed.append({'path':path,'reason':'external-canonical-review-required'});continue
        issues=[]; t=norm(title(s)).casefold();d=norm(meta(s,'name','description')).casefold()
        if not title(s) or (BRAND not in title(s) and EN.lower() not in title(s).lower()):issues.append('title')
        if t and tc[t]>1:issues.append('title-duplicate')
        if not meta(s,'name','description'):issues.append('description')
        if d and dc[d]>1:issues.append('description-duplicate')
        if curcan!=can:issues.append('canonical')
        if not meta(s,'name','robots') or 'index' not in robots or 'follow' not in robots:issues.append('indexability')
        if lang(s).lower() not in ('ar','ar-sa','ar-jo'):issues.append('lang')
        if meta(s,'property','og:url')!=can or meta(s,'property','og:title')!=title(s) or meta(s,'property','og:description')!=meta(s,'name','description') or meta(s,'property','og:locale')!='ar_AR' or meta(s,'property','og:site_name')!=BRAND:issues.append('og')
        if meta(s,'name','twitter:title')!=title(s) or meta(s,'name','twitter:description')!=meta(s,'name','description') or not meta(s,'name','twitter:card'):issues.append('twitter')
        if MARKER not in s:issues.append('schema')
        if can not in sector_locs:issues.append('sitemap')
        if not issues:skipped['already-optimal']+=1;continue
        candidates.append((len(set(issues)),path,p,sorted(set(issues))))
    candidates.sort(key=lambda x:(-x[0],x[1]));changed=[];totals=Counter();sitemap_urls=[]
    for _,path,p,issues in candidates:
        if len(changed)>=TARGET:break
        old=raw[p]; t=norm(title(old)).casefold(); d=norm(meta(old,'name','description')).casefold()
        new,changes,err=enhance(old,p,tc[t]>1 if t else False,dc[d]>1 if d else False)
        if err:failed.append({'path':path,'reason':err});continue
        ok,err=verify(new,p)
        if not ok:failed.append({'path':path,'reason':err or 'validation-failed'});continue
        intent,qs=queries(new,path)
        if len(qs)<500:failed.append({'path':path,'reason':f'semantic-map-{len(qs)}'});continue
        if body_sha(new)!=body_sha(old):failed.append({'path':path,'reason':'visible-body-integrity'});continue
        sitemap_change=expected_canonical(p) not in sector_locs
        if new==old and not sitemap_change:skipped['no-op']+=1;continue
        if new!=old:p.write_text(new,encoding='utf-8')
        if sitemap_change:sitemap_urls.append(expected_canonical(p));changes.append('sitemap')
        post=new if new!=old else old
        state['pages'][path]={'pre_sha256':sha(old),'post_sha256':sha(post),'visible_body_sha256':body_sha(post),'optimized_at':NOW,'canonical':expected_canonical(p),'version':'technical-seo-v4'}
        manifest['pages'][path]={'canonical':expected_canonical(p),'primary_intent':intent,'query_count':500,'queries':qs,'source_body_fingerprint':body_sha(post),'updated_at':NOW}
        changes=sorted(set(changes));changed.append({'path':path,'canonical':expected_canonical(p),'issues_before':issues,'changes':changes});totals.update(changes)
    sitemap_added=append_sector_urls(sitemap_urls)
    index_registered=ensure_sector_sitemap_registered()
    state.update({'version':4,'last_run_at':NOW,'last_success_count':len(changed)});manifest.update({'version':4,'updated_at':NOW,'minimum_queries_per_page':500})
    save(STATE,state);save(MANIFEST,manifest)
    ET.parse(SECTOR_SITEMAP)
    if SITEMAP_INDEX.exists():ET.parse(SITEMAP_INDEX)
    final_locs=existing_locs(SECTOR_SITEMAP); missing_after=[x['canonical'] for x in changed if x['canonical'] not in final_locs]
    intents=Counter(norm(v.get('primary_intent','')).casefold() for v in manifest['pages'].values() if v.get('primary_intent'))
    report={'sector':'ذوو الاحتياجات الخاصة والتربية الدامجة','scope':['/special-needs/','/inclusive-education/'],'actual_scope_roots':[str(x.relative_to(ROOT)) for x in SCOPES if x.exists()],'missing_scope_roots':[str(x.relative_to(ROOT)) for x in SCOPES if not x.exists()],'run_at':NOW,'target':TARGET,'success':len(changed),'status':'complete' if len(changed)>=TARGET else 'incomplete','scope_html_pages':len(raw),'candidate_pages':len(candidates),'eligible_remaining':max(0,len(candidates)-len(changed)),'skipped_noop':sum(skipped.values()),'skipped_breakdown':dict(skipped),'failed':len(failed),'failures':failed[:200],'change_totals':dict(totals),'sitemap_urls_added':sitemap_added,'sitemap_index_registered':index_registered,'changed_pages':changed,'verification':{'visible_body_unchanged':True,'json_ld_validated':True,'canonical_self_checked':True,'og_twitter_consistency_checked':True,'robots_indexability_checked':True,'locale_lang_checked':True,'sector_sitemap_xml_valid':True,'sector_sitemap_registration_checked':True,'sitemap_missing_after_success':missing_after,'semantic_queries_per_success':500,'exact_primary_intent_overlap_groups':sum(v>1 for v in intents.values())}}
    save(REPORT,report);print(json.dumps(report,ensure_ascii=False,indent=2))
    if len(changed)<TARGET and report['eligible_remaining']>0:return 3
    return 0
if __name__=='__main__':sys.exit(main())
