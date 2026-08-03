from pathlib import Path
import json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def test_quick_info():
 api=json.loads((ROOT/"api/v1/quick-info.json").read_text(encoding="utf-8")); assert api["count"]==150; assert len(list((ROOT/"quick-info").glob("*/index.html")))==150; assert len({x["slug"] for x in api["items"]})==150
 for item in api["items"]:
  p=ROOT/"quick-info"/item["slug"]/"index.html"; s=p.read_text(encoding="utf-8"); assert "max-image-preview:large" in s and '"Article"' in s and '"FAQPage"' in s and "المصادر المحورية" in s
  with Image.open(ROOT/"assets/quick-info/cards"/(item["slug"]+".png")) as im: assert im.size==(1280,720)
 sm=(ROOT/"sitemap-quick-info.xml").read_text(encoding="utf-8"); assert sm.count("<url>")==151; assert "sitemap-quick-info.xml" in (ROOT/"sitemap-index.xml").read_text(encoding="utf-8")
 assert 'href="/quick-info/"' in (ROOT/"index.html").read_text(encoding="utf-8")
