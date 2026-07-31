from __future__ import annotations
import json,re,shutil,subprocess,tempfile,unittest,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"content/v214/special-needs-guides-manifest-ar.json"
GUIDES=ROOT/"content/v214/special-needs-guides"
PUBLISHER=ROOT/"scripts/publish_special_needs_guides_v214.py"
BASE="https://healthrenewal.org"
NS={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
BANNED=re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")
HOSTS={"www.who.int","www.unicef.org","www.un.org","social.desa.un.org","www.undrr.org"}

class Text(HTMLParser):
    def __init__(self): super().__init__();self.skip=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in {"script","style","svg"}: self.skip+=1
    def handle_endtag(self,tag):
        if tag in {"script","style","svg"} and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(data.strip())

class V214(unittest.TestCase):
    def data(self):
        m=json.loads(MANIFEST.read_text(encoding="utf-8"))
        return m,{s:json.loads((GUIDES/f"{s}.json").read_text(encoding="utf-8")) for s in m["guide_slugs"]}
    def site(self,index=False):
        p=Path(tempfile.mkdtemp(prefix="v214-"));self.addCleanup(lambda:shutil.rmtree(p,ignore_errors=True))
        (p/"special-needs").mkdir(parents=True)
        (p/"special-needs/index.html").write_text('<html lang="ar" dir="rtl"><body><div class="resources"></div></body></html>',encoding="utf-8")
        (p/"sitemap-special-needs.xml").write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>',encoding="utf-8")
        xml='<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>'+BASE+'/sitemap-core.xml</loc></sitemap></sitemapindex>' if index else '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>'
        (p/"sitemap.xml").write_text(xml,encoding="utf-8");return p
    def run_publisher(self,site):
        r=subprocess.run(["python3",str(PUBLISHER),str(site)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads((site/"api/special-needs-guides-v214.json").read_text(encoding="utf-8"))
    def test_contract_and_no_overlap(self):
        m,g=self.data();self.assertEqual((m["version"],m["status"],m["external_review"]),(214,"internally-reviewed","recommended-not-completed"));self.assertEqual(len(g),5)
        old=set()
        for v in (209,210,211,212):old.update(json.loads((ROOT/f"content/v{v}/special-needs-guides-manifest-ar.json").read_text(encoding="utf-8"))["guide_slugs"])
        self.assertTrue(set(g).isdisjoint(old))
        for src in m["sources"].values():self.assertEqual(urlparse(src["url"]).scheme,"https");self.assertIn(urlparse(src["url"]).netloc,HOSTS)
        for slug,x in g.items():
            self.assertEqual(x["slug"],slug);self.assertEqual(x["review_status"],"internally-reviewed");self.assertEqual(x["external_review"],"recommended-not-completed")
            self.assertGreaterEqual(len(x["intro"]),3);self.assertGreaterEqual(len(x["sections"]),5);self.assertTrue(all(len(s["paragraphs"])>=3 for s in x["sections"]))
            self.assertGreaterEqual(len(x["checklist"]),7);self.assertGreaterEqual(len(x["common_mistakes"]),5);self.assertGreaterEqual(len(x["template"]),8);self.assertGreaterEqual(len(x["source_ids"]),2)
            self.assertGreaterEqual(len(re.findall(r"[\w\u0600-\u06ff]+",json.dumps(x,ensure_ascii=False))),900);self.assertTrue(90<=len(x["description"])<=180);self.assertIsNone(BANNED.search(json.dumps(x,ensure_ascii=False)))
    def test_pages_sitemaps_and_idempotence(self):
        s=self.site();a=self.run_publisher(s);b=self.run_publisher(s);self.assertEqual((a["guide_count"],b["generated_page_count"]),(5,5));self.assertGreaterEqual(a["minimum_source_words"],900)
        hub=(s/"special-needs/index.html").read_text(encoding="utf-8");self.assertEqual(hub.count("special-needs-guides-v214:start"),1);self.assertEqual(hub.count("special-needs-guides-v214:end"),1)
        for slug in self.data()[0]["guide_slugs"]:
            page=(s/f"special-needs/{slug}/index.html").read_text(encoding="utf-8");self.assertIn('lang="ar" dir="rtl"',page);self.assertIn('rel="canonical"',page);self.assertIn("application/ld+json",page);self.assertIn("متى نطلب مساعدة متخصصة؟",page);self.assertIsNone(BANNED.search(page))
            t=Text();t.feed(page);self.assertGreaterEqual(len(re.findall(r"[\w\u0600-\u06ff]+"," ".join(t.parts))),1000)
        locs=[n.text for n in ET.parse(s/"sitemap-special-needs.xml").findall("sm:url/sm:loc",NS)]
        self.assertEqual(len([u for u in locs if u and any(x in u for x in self.data()[0]["guide_slugs"])]),5)
    def test_sitemapindex(self):
        s=self.site(True);self.run_publisher(s);self.run_publisher(s);tree=ET.parse(s/"sitemap.xml");self.assertEqual(tree.getroot().tag.rsplit("}",1)[-1],"sitemapindex")
        self.assertEqual([n.text for n in tree.findall("sm:sitemap/sm:loc",NS)].count(BASE+"/sitemap-special-needs.xml"),1)

if __name__=="__main__":unittest.main()
