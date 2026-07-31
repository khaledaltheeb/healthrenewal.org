from __future__ import annotations
import hashlib, importlib.util, json, re, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"content"/"v281"/"conditions-50-ar.json.zlib.b64"
V280=ROOT/"content"/"v280"/"capabilities-100-ar.json"
PUBLISHER=ROOT/"scripts"/"publish_conditions_v281.py"
PUB_WORKFLOW=ROOT/".github"/"workflows"/"publish-capabilities-v281.yml"
DEPLOY_WORKFLOW=ROOT/".github"/"workflows"/"deploy-capabilities-v281.yml"

def load_publisher():
    spec=importlib.util.spec_from_file_location("v281",PUBLISHER)
    module=importlib.util.module_from_spec(spec); assert spec.loader
    spec.loader.exec_module(module); return module

class ConditionsV281Contract(unittest.TestCase):
    def setUp(self):
        self.data=load_publisher().load()

    def test_exactly_fifty_non_repeated_conditions(self):
        items=self.data["conditions"]
        self.assertEqual(self.data["version"],281)
        self.assertEqual(len(items),50)
        self.assertEqual([x["rank"] for x in items],list(range(101,151)))
        self.assertEqual(len({x["slug"] for x in items}),50)
        self.assertTrue(all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",x["slug"]) for x in items))
        old={x["slug"] for x in json.loads(V280.read_text(encoding="utf-8"))["conditions"]}
        self.assertFalse(old.intersection({x["slug"] for x in items}))

    def test_required_depth_sources_and_boundaries(self):
        required={"rank","slug","title_ar","title_en","category","cause","pattern","medical_focus","diagnosis","care","safety","opportunity","source_title","source_url"}
        allowed={"chromatin-syndromic","developmental-epileptic","metabolic-neurodegenerative"}
        for item in self.data["conditions"]:
            self.assertEqual(set(item),required,item["slug"])
            self.assertIn(item["category"],allowed)
            for key in ("cause","pattern","medical_focus","diagnosis","care","safety","opportunity"):
                self.assertGreaterEqual(len(item[key]),40,(item["slug"],key))
            self.assertRegex(item["source_url"],r"^https://(www\.)?(ncbi\.nlm\.nih\.gov|medlineplus\.gov|ninds\.nih\.gov)/")
        text=json.dumps(self.data,ensure_ascii=False)
        for banned in ("معاقين","اعتماد عالمي","علاج مضمون","أوقف الدواء","غيّر الجرعة"):
            self.assertNotIn(banned,text)
        self.assertIn("لا توجد مصادقة أو مراجعة سريرية خارجية مستقلة",text)

    def test_publisher_generates_fifty_deep_unique_pages(self):
        module=load_publisher()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"capabilities").mkdir(); (root/"special-needs").mkdir()
            (root/"capabilities"/"index.html").write_text("<html><body><main><h1>hub</h1></main></body></html>",encoding="utf-8")
            (root/"special-needs"/"index.html").write_text("<html><body><main><h1>sector</h1></main></body></html>",encoding="utf-8")
            (root/"sitemap.xml").write_text('<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',encoding="utf-8")
            report=module.publish(root)
            self.assertEqual((report["condition_count"],report["detail_page_count"],report["generated_page_count"]),(50,50,51))
            pages=[root/"capabilities"/c["slug"]/"index.html" for c in self.data["conditions"]]
            self.assertTrue(all(p.is_file() for p in pages))
            hashes=set()
            for condition,path in zip(self.data["conditions"],pages):
                text=path.read_text(encoding="utf-8")
                plain=re.sub(r"<[^>]+>"," ",text)
                self.assertGreaterEqual(len(re.findall(r"[\u0600-\u06ffA-Za-z0-9]+",plain)),1000,path)
                self.assertEqual(text.count("<h1"),1,path)
                self.assertGreaterEqual(text.count("<h2>"),14,path)
                self.assertIn(condition["source_url"],text)
                self.assertIn('"@type": "MedicalWebPage"',text)
                self.assertIn('rel="canonical"',text)
                self.assertNotIn("معاقين",text)
                digest=hashlib.sha256(re.sub(r"\s+"," ",plain).encode()).hexdigest()
                self.assertNotIn(digest,hashes); hashes.add(digest)
            sitemap=(root/"sitemap-capabilities-v281.xml").read_text(encoding="utf-8")
            self.assertEqual(sitemap.count("<url>"),51)
            module.publish(root)
            self.assertEqual((root/"capabilities"/"index.html").read_text(encoding="utf-8").count("capabilities-v281:start"),1)
            self.assertEqual((root/"special-needs"/"index.html").read_text(encoding="utf-8").count("capabilities-v281:start"),1)

    def test_existing_publication_chain_runs_and_verifies_v281(self):
        publish=PUB_WORKFLOW.read_text(encoding="utf-8")
        deploy=DEPLOY_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python scripts/publish_conditions_v281.py validated-site",publish)
        self.assertIn("Publish capabilities library v280",publish)
        self.assertIn("capabilities-v281.json",publish)
        self.assertIn("sitemap-capabilities-v281.xml",publish)
        self.assertIn("capabilities-v281.json",deploy)
        self.assertIn("condition_count']==50",deploy)
        self.assertIn("generated_page_count']==51",deploy)

if __name__=="__main__":
    unittest.main()
