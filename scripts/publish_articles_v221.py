#!/usr/bin/env python3
from __future__ import annotations
import json,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.articles_v221_common import BASE,INDEX,ROUTE,URL,e,load
from scripts.articles_v221_render import article,index_page
SITE=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve()

def sitemap(d):
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns)
    root=ET.Element(f'{{{ns}}}urlset')
    for url,priority in ((INDEX,'0.7'),(URL,'0.8')):
        node=ET.SubElement(root,f'{{{ns}}}url');ET.SubElement(node,f'{{{ns}}}loc').text=url;ET.SubElement(node,f'{{{ns}}}lastmod').text=d['reviewed_at'];ET.SubElement(node,f'{{{ns}}}priority').text=priority
    ET.ElementTree(root).write(SITE/'sitemap-articles.xml',encoding='utf-8',xml_declaration=True)
    path=SITE/'sitemap.xml';tree=ET.parse(path);main=tree.getroot();mode=main.tag.rsplit('}',1)[-1];changed=False
    def q(name): return (main.tag.split('}',1)[0]+'}'+name) if main.tag.startswith('{') else name
    if mode=='sitemapindex':
        target=BASE+'sitemap-articles.xml';existing={(x.text or '').strip() for x in main.findall('{*}sitemap/{*}loc')}
        if target not in existing: node=ET.SubElement(main,q('sitemap'));ET.SubElement(node,q('loc')).text=target;changed=True
    elif mode=='urlset':
        existing={(x.text or '').strip() for x in main.findall('{*}url/{*}loc')}
        for url in (INDEX,URL):
            if url not in existing: node=ET.SubElement(main,q('url'));ET.SubElement(node,q('loc')).text=url;changed=True
    else: raise SystemExit('unsupported sitemap')
    if changed: tree.write(path,encoding='utf-8',xml_declaration=True)
    return {'mode':mode,'registered':True,'urls':2}

def link_magazine(d):
    path=SITE/'magazine/index.html'
    if not path.is_file(): raise SystemExit('magazine missing')
    text=path.read_text(encoding='utf-8');marker='<section><h2>قائمة فحص كل مادة علمية</h2>';identity='data-articles-v221'
    if identity not in text:
        if marker not in text: raise SystemExit('magazine marker missing')
        block=f'<section {identity}><h2>مقالات منشورة</h2><article><h3>{e(d["title"])}</h3><p>{e(d["description"])}</p><p><a href="/pterminology-site/{ROUTE}">قراءة المقال</a></p></article></section>'
        text=text.replace(marker,block+marker,1)
    if text.count(identity)!=1 or text.count(f'href="/pterminology-site/{ROUTE}"')!=1: raise SystemExit('duplicate magazine link')
    path.write_text(text,encoding='utf-8');return True

def publish():
    if not SITE.is_dir(): raise SystemExit('site missing')
    d=load();target=SITE/ROUTE/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(article(d),encoding='utf-8')
    index=SITE/'articles/index.html';index.parent.mkdir(parents=True,exist_ok=True);index.write_text(index_page(d),encoding='utf-8')
    report={'version':221,'articles':1,'pages':2,'article_route':ROUTE,'review_status':d['review_status'],'source_publication_status':d['publication_status'],'moderate_risk':True,'authoritative_sources':len(d['sources']),'magazine_linked':link_magazine(d),'sitemap':sitemap(d),'live_verified':False}
    api=SITE/'api';api.mkdir(parents=True,exist_ok=True);(api/'articles-v221.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return report
if __name__=='__main__': publish()
