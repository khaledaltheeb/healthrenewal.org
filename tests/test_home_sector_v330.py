from __future__ import annotations
import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import verify_home_sector_v330 as verifier
class HomeSectorTests(unittest.TestCase):
 def test_complete_sector_passes(self):
  report=verifier.validate();self.assertEqual(report["status"],"passed",report);self.assertEqual(len(report["pages"]),4)
 def mutate(self,name,old,new):
  source=verifier.PAGES[name].read_text(encoding="utf-8");self.assertIn(old,source)
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"index.html";path.write_text(source.replace(old,new,1),encoding="utf-8");return verifier.validate_page(name,path)
 def test_rejects_removed_emergency_boundary(self):
  result=self.mutate("index","الأخطار المنزلية والطبية تسبق تحسين الروتين","تنبيه عام");self.assertEqual(result["status"],"failed")
 def test_rejects_diagnosis_claim(self):
  result=self.mutate("library","لا تقدم تشخيصًا من شكل الغرفة أو الروتين","تقدم علاج مضمون من شكل الغرفة");self.assertEqual(result["status"],"failed");self.assertTrue(any("banned pattern" in e for e in result["errors"]))
 def test_rejects_bad_canonical(self):
  result=self.mutate("assessment",verifier.CANONICALS["assessment"],"https://example.com/wrong/");self.assertEqual(result["status"],"failed")
 def test_rejects_removed_harm_boundary(self):
  result=self.mutate("interventions","قاعدة منع الضرر","ملاحظة عامة");self.assertEqual(result["status"],"failed")
if __name__=="__main__":unittest.main()