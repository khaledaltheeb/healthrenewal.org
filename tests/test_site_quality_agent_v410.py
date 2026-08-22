from __future__ import annotations
import importlib.util,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('site_quality_agent_v410',ROOT/'scripts/site_quality_agent_v410.py')
assert SPEC and SPEC.loader
agent=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(agent)

class TestSiteQualityAgentV410(unittest.TestCase):
 def test_contrast(self):
  self.assertAlmostEqual(agent.contrast('#000','#fff') or 0,21.0,places=2)
  self.assertLess(agent.contrast('#777','#fff') or 99,4.5)
 def test_page_audit_finds_core_problems(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'care-guides/demo/index.html';p.parent.mkdir(parents=True)
   p.write_text('<!doctype html><html><head></head><body><section class="hero" style="background:#fff"><h1>دعم الطفل أثناء العلاج</h1><p>نص قصير عن العلاج.</p><a href="/missing/">رابط</a><img src="x.jpg"></section></body></html>',encoding='utf-8')
   item=agent.page_score(p,root)
   self.assertIn('missing_title',item['findings']);self.assertIn('broken_internal_links',item['findings']);self.assertIn('images_missing_alt',item['findings']);self.assertIn('hero_inline_background_without_explicit_text_color',item['findings']);self.assertEqual(item['risk'],'high')
 def test_research_query_prefers_english_route(self):
  item={'route':'care-guides/pediatric-cancer-child-decision-participation/','title':'مشاركة الطفل في القرار','h1':'مشاركة الطفل'}
  q=agent.query(item);self.assertIn('pediatric',q);self.assertIn('cancer',q);self.assertNotRegex(q,r'[\u0600-\u06ff]')

if __name__=='__main__':unittest.main()
