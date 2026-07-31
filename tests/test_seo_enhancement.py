from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_homepage_contains_faq_schema_and_advanced_meta_tags():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'meta name="keywords"' in html
    assert 'meta property="og:title"' in html
    assert 'meta property="twitter:description"' in html
    assert 'FAQPage' in html


def test_secondary_page_has_professional_seo_meta_tags():
    html = (ROOT / "accessibility" / "index.html").read_text(encoding="utf-8")
    assert '<link rel="canonical"' in html
    assert 'meta name="description"' in html
    assert 'meta property="og:url"' in html
