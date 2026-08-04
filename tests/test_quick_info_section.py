from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 250
NEW_SLUGS = ['accountability-vs-self-blame', 'advice-vs-control', 'build-personal-overwhelm-plan', 'caregiver-resentment-check', 'child-opposition-vs-overwhelm', 'child-sensory-overload-check', 'confidence-vs-defensiveness', 'conflict-repair-check', 'create-sleep-wind-down', 'decision-fatigue-check', 'disappointment-vs-hopelessness', 'empathy-vs-emotional-absorption', 'explain-mental-health-to-child', 'family-emotional-safety-check', 'fatigue-vs-sleepiness', 'five-factors-caregiver-guilt', 'five-factors-low-self-worth', 'five-factors-social-exhaustion', 'five-factors-sunday-anxiety', 'five-factors-workplace-anxiety', 'five-reasons-boundary-guilt', 'five-reasons-children-lie', 'five-reasons-emotional-distance', 'five-reasons-relationship-doubt', 'five-reasons-restless-sleep', 'focus-break-vs-digital-distraction', 'forgiveness-vs-reconciliation', 'friendship-balance-check', 'handle-workplace-gossip', 'healthy-anger-vs-aggression', 'help-teen-friendship-breakup', 'manage-family-boundaries-holidays', 'openness-vs-oversharing', 'panic-avoidance-check', 'prepare-child-first-therapy-session', 'prepare-therapy-intake-session', 'rebuild-routine-after-low-mood', 'recover-from-people-pleasing', 'resilience-vs-emotional-denial', 'respond-to-body-comments', 'return-to-work-after-burnout', 'routine-vs-rigidity', 'sleep-debt-check', 'stop-ruminating-after-embarrassment', 'support-partner-with-anxiety', 'support-vs-enabling', 'talk-about-therapy-with-family', 'teen-privacy-vs-withdrawal', 'therapy-readiness-check', 'workplace-bullying-check']

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
    assert "250 صفحة" in (ROOT / "quick-info/index.html").read_text(encoding="utf-8")
    assert 'href="/quick-info/"' in (ROOT / "index.html").read_text(encoding="utf-8")
