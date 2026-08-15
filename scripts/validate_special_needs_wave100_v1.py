#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
MARK='rawafid-wave100-v1'
def visible_words(src):
    src=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',src,flags=re.I|re.S)
    src=re.sub(r'<[^>]+>',' ',src)
    return len(re.findall(r'[\u0600-\u06FFA-Za-z0-9]+',src))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('site',nargs='?',default='_site');ap.add_argument('--minimum-words',type=int,default=1200);a=ap.parse_args()
    site=Path(a.site); root=site/'special-needs'/'knowledge'; pages=[]; failures=[]
    for f in sorted(root.glob('*/index.html')):
        src=f.read_text(encoding='utf-8',errors='replace')
        if MARK not in src: continue
        slug=f.parent.name; words=visible_words(src); is_hub='خريطة موضوعية' in src or 'خريطة مرجعية' in src
        refs=len(re.findall(r'<li><a href="https?://',src))
        checks={'canonical':bool(re.search(r'<link rel="canonical" href="https://healthrenewal\.org/special-needs/knowledge/',src)),'indexable':'noindex' not in src.lower(),'h1':src.count('<h1>')==1,'faq_schema':'FAQPage' in src if not is_hub else True,'article_schema':'"Article"' in src if not is_hub else True,'trusted_sources':refs>=2 if not is_hub else True,'visible_words':words}
        if (not is_hub and words<a.minimum_words) or not all(v for k,v in checks.items() if k!='visible_words'):
            failures.append({'slug':slug,'hub':is_hub,'checks':checks})
        pages.append({'slug':slug,'hub':is_hub,'visibleWords':words,'sourceLinks':refs})
    topic=[p for p in pages if not p['hub']]; hubs=[p for p in pages if p['hub']]
    report={'schemaVersion':1,'status':'passed' if len(pages)==100 and len(topic)==90 and len(hubs)==10 and not failures else 'failed','pages':len(pages),'topicPages':len(topic),'hubPages':len(hubs),'minimumVisibleTopicWords':min((p['visibleWords'] for p in topic),default=0),'minimumSourceLinks':min((p['sourceLinks'] for p in topic),default=0),'failures':failures}
    api=site/'api';api.mkdir(parents=True,exist_ok=True);(api/'special-needs-wave100-visible-quality-v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if report['status']=='passed' else 1)
if __name__=='__main__':main()
