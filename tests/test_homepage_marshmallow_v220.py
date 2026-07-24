from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


class StrictHTMLParser(HTMLParser):
    pass


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    StrictHTMLParser().feed(source)
    body = source.split("<body>", 1)[1].split("</body>", 1)[0]

    assert source.count('class="nav-group"') == 3
    assert 'class="desktop-nav"' in source
    assert 'class="mobile-nav"' in source
    assert "@media(max-width:980px)" in source
    assert ".desktop-nav{display:none}" in source
    assert ".mobile-nav{display:block;position:relative}" in source

    assert "--marshmallow-mint:#edf8f5" in source
    assert "--marshmallow-lilac:#f3effa" in source
    assert "--marshmallow-rose:#fff0f5" in source
    assert "--marshmallow-peach:#fff4ec" in source
    assert "background:#071827" not in source
    assert "background:#000" not in source

    assert ".hero h1{max-width:12ch" in source
    assert "font-size:clamp(2.65rem,4.2vw,4rem)" in source
    assert "font-size:clamp(2.35rem,10.6vw,3.55rem)" in source
    assert "<h1><span>افهم الحالة.</span><span>اختر الخطوة الأنسب.</span></h1>" in source

    actions = re.search(r'<div class="actions">(.*?)</div>', source, re.DOTALL)
    assert actions
    assert len(re.findall(r"<a\b", actions.group(1))) == 3

    assert "واجهة API للدورات" not in body
    assert "فتح واجهة API" not in body
    assert '<a href="api/" hidden aria-hidden="true" tabindex="-1"></a>' in body
    assert ">API<" not in body

    assert "بوابات كانت غير ظاهرة بوضوح" not in source
    assert "أصبحت هذه البوابات" not in source
    assert len(re.findall(r"<h1\b", source)) == 1
    assert len(re.findall(r"<h2\b", source)) >= 5
    assert len(re.findall(r"<h3\b", source)) >= 22

    for route in (
        "encyclopedia/",
        "comparisons/",
        "library/",
        "hubs/",
        "care-guides/",
        "special-needs/",
        "guided-assessment/",
        "assessments/",
        "cognitive-tests/",
        "assessment-lab/",
        "cognitive-lab/",
        "provider-assessment-demo/",
    ):
        assert f'href="{route}"' in source

    print("homepage-marshmallow-layout-v220: passed")


if __name__ == "__main__":
    main()
