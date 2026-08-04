from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "special-needs/conditions/cerebral-palsy"
URL = "https://healthrenewal.org/special-needs/conditions/cerebral-palsy/"
PAGES = {
    "index.html": URL,
    "detection-diagnosis/index.html": URL + "detection-diagnosis/",
    "movement-rehabilitation/index.html": URL + "movement-rehabilitation/",
    "health-lifespan/index.html": URL + "health-lifespan/",
    "communication-education/index.html": URL + "communication-education/",
    "family-adulthood/index.html": URL + "family-adulthood/",
}

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.h1=0; self.lang=None; self.direction=None; self.canonicals=[]; self.ids=set(); self.hrefs=[]; self.jsonld=[]; self.in_json=False; self.parts=[]
    def handle_starttag(self, tag, attrs):
        v=dict(attrs)
        if tag=="html": self.lang=v.get("lang"); self.direction=v.get("dir")
        if tag=="h1": self.h1+=1
        if v.get("id"): self.ids.add(v["id"])
        if tag=="a" and v.get("href"): self.hrefs.append(v["href"])
        if tag=="link" and "canonical" in v.get("rel","").split(): self.canonicals.append(v.get("href",""))
        if tag=="script" and v.get("type")=="application/ld+json": self.in_json=True; self.parts=[]
    def handle_endtag(self, tag):
        if tag=="script" and self.in_json: self.jsonld.append("".join(self.parts)); self.in_json=False
    def handle_data(self,data):
        if self.in_json: self.parts.append(data)

def types(value):
    out=set()
    if isinstance(value,dict):
        t=value.get("@type")
        if isinstance(t,str): out.add(t)
        elif isinstance(t,list): out.update(x for x in t if isinstance(x,str))
        for child in value.values(): out.update(types(child))
    elif isinstance(value,list):
        for child in value: out.update(types(child))
    return out

def test_cerebral_palsy_publication_contract():
    failures=[]; combined=""; total=0
    for relative,canonical in PAGES.items():
        path=BASE/relative
        if not path.is_file(): failures.append(f"missing page: {relative}"); continue
        text=path.read_text(encoding="utf-8"); combined += "\n"+text; total += len(text)
        minimum=9000 if relative=="index.html" else 6500
        if len(text)<minimum: failures.append(f"page too short: {relative} {len(text)}")
        if "khaledaltheeb.github.io" in text or "pterminology-site" in text: failures.append(f"legacy domain: {relative}")
        if re.search(r'<meta\s+[^>]*name=["\']keywords["\']',text,re.I): failures.append(f"meta keywords: {relative}")
        p=Parser(); p.feed(text)
        if (p.lang,p.direction)!=("ar","rtl"): failures.append(f"language/dir: {relative}")
        if p.h1!=1: failures.append(f"H1 count {relative}: {p.h1}")
        if p.canonicals!=[canonical]: failures.append(f"canonical {relative}: {p.canonicals}")
        if "main" not in p.ids: failures.append(f"missing main: {relative}")
        schemas=[]
        for raw in p.jsonld:
            try: schemas.append(json.loads(raw))
            except json.JSONDecodeError as exc: failures.append(f"jsonld {relative}: {exc}")
        if not {"MedicalWebPage","BreadcrumbList"}.issubset(types(schemas)): failures.append(f"schema: {relative}")
        for href in p.hrefs:
            if href.startswith("#") and href[1:] and href[1:] not in p.ids: failures.append(f"anchor {href}: {relative}")
    if total<52000: failures.append(f"combined content too short: {total}")
    try:
        evidence_text=(BASE/"evidence.json").read_text(encoding="utf-8"); evidence=json.loads(evidence_text); combined += evidence_text
    except Exception as exc: failures.append(f"evidence invalid: {exc}"); evidence={}
    if len(evidence.get("sources",[]))<14: failures.append("need at least 14 sources")
    if len(evidence.get("claim_matrix",[]))<7: failures.append("need at least 7 mapped claims")
    required=["GMA","HINE","GMFCS","MACS","CFCS","EDACS","VFCS","التشنج","خلل التوتر","مراقبة الورك","نسبة الهجرة","البلع","التنفس","AAC","البوتولينوم","الباكلوفين","SDR","القرار المدعوم","خطة الطوارئ","33999106","32086598"]
    for term in required:
        if term not in combined: failures.append(f"missing concept: {term}")
    hub=(BASE/"index.html").read_text(encoding="utf-8")
    for relative in list(PAGES)[1:]:
        if f'href="{relative.removesuffix("index.html")}"' not in hub: failures.append(f"hub missing: {relative}")
    try:
        root=ET.parse(ROOT/"sitemap-cerebral-palsy.xml").getroot(); ns={"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}; locations={n.text for n in root.findall("s:url/s:loc",ns)}
    except Exception as exc: failures.append(f"sitemap invalid: {exc}"); locations=set()
    if locations!=set(PAGES.values()): failures.append(f"sitemap mismatch: {locations ^ set(PAGES.values())}")
    if "https://healthrenewal.org/sitemap-cerebral-palsy.xml" not in (ROOT/"sitemap-index.xml").read_text(encoding="utf-8"): failures.append("sitemap not indexed")
    assert not failures, "\n".join(failures)
