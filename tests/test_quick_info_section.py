from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 200
NEW_SLUGS = ['ambition-vs-overwork', 'ask-reassurance-without-dependency', 'authentic-self-relationship-check', 'boredom-vs-low-mood', 'child-hidden-school-distress-check', 'closeness-vs-enmeshment', 'co-parenting-after-separation', 'compassion-fatigue-vs-indifference', 'digital-boundaries-relationship', 'discipline-vs-punishment', 'emotional-numbness-vs-calm', 'emotionally-unavailable-check', 'emotionally-unavailable-parent', 'end-friendship-respectfully', 'financial-abuse-signs', 'five-factors-adhd-symptoms', 'five-factors-breakup-recovery', 'five-factors-emotional-exhaustion', 'five-factors-night-loneliness', 'five-reasons-compliments-uncomfortable', 'five-reasons-freeze-under-pressure', 'five-reasons-indecision', 'five-reasons-morning-anxiety', 'five-reasons-repeated-arguments', 'five-reasons-school-refusal', 'grief-support-check', 'grounding-after-nightmare', 'guilt-after-saying-no', 'guilt-vs-shame', 'health-awareness-vs-health-anxiety', 'high-standards-vs-perfectionism', 'nightmare-sleep-fear-check', 'over-responsibility-check', 'patience-vs-emotional-suppression', 'post-trauma-caution-vs-ptsd', 'prepare-psychiatry-appointment', 'privacy-vs-secrecy', 'protect-child-adult-conflict', 'reduce-doomscrolling', 'repair-after-argument', 'respond-passive-aggression', 'restlessness-vs-hyperactivity', 'return-social-life-after-isolation', 'self-care-vs-avoidance', 'self-criticism-check', 'sensory-preference-vs-avoidance', 'social-media-mood-check', 'survival-mode-check', 'work-follows-home-check', 'workplace-boundaries-manager']

def test_quick_info():
    api = json.loads((ROOT / "api/v1/quick-info.json").read_text(encoding="utf-8"))
    assert api["count"] == EXPECTED
    assert len(api["items"]) == EXPECTED
    assert len(list((ROOT / "quick-info").glob("*/index.html"))) == EXPECTED
    assert len({item["slug"] for item in api["items"]}) == EXPECTED
    assert len({item["title"] for item in api["items"]}) == EXPECTED
    assert set(NEW_SLUGS).issubset({item["slug"] for item in api["items"]})
    for item in api["items"]:
        page = ROOT / "quick-info" / item["slug"] / "index.html"
        source = page.read_text(encoding="utf-8")
        assert "max-image-preview:large" in source
        assert '"Article"' in source
        assert '"FAQPage"' in source
        assert "المصادر المحورية" in source
        assert item["url"] in source
        with Image.open(ROOT / "assets/quick-info/cards" / (item["slug"] + ".png")) as image:
            assert image.size == (1280, 720)
    sitemap = (ROOT / "sitemap-quick-info.xml").read_text(encoding="utf-8")
    assert sitemap.count("<url>") == EXPECTED + 1
    assert "sitemap-quick-info.xml" in (ROOT / "sitemap-index.xml").read_text(encoding="utf-8")
    hub = (ROOT / "quick-info/index.html").read_text(encoding="utf-8")
    assert "200 صفحة" in hub
    assert 'href="/quick-info/"' in (ROOT / "index.html").read_text(encoding="utf-8")
