#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH="automation/addiction-condition-guides-clean-v1"
SOURCE_BRANCH="agent/addiction-condition-guides-v2-20260803"
OLD_SHA="717927d839784e453091d3086d17ae3689251f93545c1b1222e119473c1f0d63"
NEW_SHA="e24de57695370943a33b6e4bf80cdfa5fb5763e3fb7219b06899a3ae6fd14758"

if [[ -f addiction/cannabis-use-disorder/index.html && -f api/addiction-condition-guides-v2.json ]]; then
  echo "Clean condition-guide publication already exists."
  exit 0
fi

git fetch origin "${SOURCE_BRANCH}"
mkdir -p content/addiction scripts
git show "origin/${SOURCE_BRANCH}:content/addiction/condition-guides-v2.part00.b64" > content/addiction/condition-guides-v2.part00.b64
git show "origin/${SOURCE_BRANCH}:content/addiction/condition-guides-v2.part01.b64" > content/addiction/condition-guides-v2.part01.b64
git show "origin/${SOURCE_BRANCH}:scripts/materialize_addiction_condition_guides_v2.py" > scripts/materialize_addiction_condition_guides_v2.py

python - <<PY
from pathlib import Path
path = Path("scripts/materialize_addiction_condition_guides_v2.py")
text = path.read_text(encoding="utf-8")
old = "${OLD_SHA}"
new = "${NEW_SHA}"
if old not in text:
    raise SystemExit("Historical payload checksum marker not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY

python scripts/materialize_addiction_condition_guides_v2.py .

python - <<'PY'
from pathlib import Path

path = Path("addiction/index.html")
text = path.read_text(encoding="utf-8")
text = text.replace(
    "مع سلامة الانسحاب و100 بروتوكول منظم وخطط تعافٍ ومسارات للشخص والأسرة والمدرب والمجتمع والمعالج.",
    "مع سلامة الانسحاب و100 بروتوكول منظم وعشرة ملفات حالات مفصلة وخطط تعافٍ ومسارات للشخص والأسرة والمدرب والمجتمع والمعالج.",
)
text = text.replace(
    '<span class="tag">100 بروتوكول منظم</span><span class="tag">5 مسارات جمهور</span>',
    '<span class="tag">100 بروتوكول منظم</span><span class="tag">10 ملفات حالات</span><span class="tag">5 مسارات جمهور</span>',
)
if '/addiction/conditions/' not in text:
    text = text.replace(
        '<a href="/addiction/audiences/">حسب الجمهور</a>',
        '<a href="/addiction/audiences/">حسب الجمهور</a><a href="/addiction/conditions/">ملفات الحالات</a><a href="/addiction/methodology/">المنهجية</a>',
    )
    text = text.replace(
        '<a class="button secondary" href="/addiction/protocol-atlas/">افتح 100 بروتوكول</a>',
        '<a class="button secondary" href="/addiction/conditions/">افتح ملفات الحالات العشر</a><a class="button secondary" href="/addiction/protocol-atlas/">افتح 100 بروتوكول</a>',
    )
links = {
    "الكحول": "alcohol-use-disorder",
    "الأفيونات": "opioid-use-disorder",
    "المنشطات": "stimulant-use-disorder",
    "القنب": "cannabis-use-disorder",
    "المهدئات والبنزوديازيبينات": "sedative-benzodiazepine-use-disorder",
    "النيكوتين والتبغ": "nicotine-tobacco-dependence",
    "المقامرة": "gambling-related-harms",
    "الألعاب الرقمية": "gaming-disorder",
    "المستنشقات": "inhalant-use-disorder",
    "الاستخدام المتعدد": "polysubstance-use-and-overdose-risk",
}
for label, slug in links.items():
    text = text.replace(
        f"<h3>{label}</h3>",
        f'<h3><a href="/addiction/{slug}/">{label}</a></h3>',
    )
path.write_text(text, encoding="utf-8")
PY

cat > tests/test_addiction_condition_guides_v2.py <<'PY'
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://healthrenewal.org/"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
SLUGS = (
    "alcohol-use-disorder",
    "opioid-use-disorder",
    "stimulant-use-disorder",
    "cannabis-use-disorder",
    "nicotine-tobacco-dependence",
    "sedative-benzodiazepine-use-disorder",
    "gambling-related-harms",
    "gaming-disorder",
    "inhalant-use-disorder",
    "polysubstance-use-and-overdose-risk",
)
AUDIENCES = ("person", "family", "trainer", "community", "clinician")
REQUIRED = (
    '<html lang="ar" dir="rtl">',
    "<title>",
    'name="description"',
    'rel="canonical"',
    "<h1",
    'type="application/ld+json"',
)
BANNED = ("جرعة:", " ملغ", " mg ", "خفض الجرعة بنسبة", "تناول حبة")


def test_condition_guides_are_static_complete_and_safe() -> None:
    manifest = json.loads(
        (ROOT / "addiction" / "editorial-manifest.json").read_text(encoding="utf-8")
    )
    pages = manifest.get("condition_pages", [])
    assert manifest.get("version") == "2.0.0"
    assert manifest.get("integration", {}).get("extends_existing_center") is True
    assert len(pages) == 10
    assert sum(int(item.get("protocol_count", 0)) for item in pages) == 100

    combined: list[str] = []
    for slug in SLUGS:
        page = ROOT / "addiction" / slug / "index.html"
        assert page.is_file(), slug
        text = page.read_text(encoding="utf-8")
        assert all(marker in text for marker in REQUIRED), slug
        assert text.count('class="protocol"') == 10, slug
        assert "الطوارئ" in text, slug
        assert "/addiction/sources/" in text, slug
        assert "/addiction/evidence-library/" not in text, slug
        assert "/addiction/recovery-plan/" not in text, slug
        combined.append(text)

    joined = "\n".join(combined)
    assert not [fragment for fragment in BANNED if fragment in joined]

    report = json.loads(
        (ROOT / "api" / "addiction-condition-guides-v2.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "passed"
    assert report["centerPages"] >= 18
    assert report["conditionPages"] == 10
    assert report["detailedProtocols"] == 100
    assert report["sourceRegistryEntries"] >= 50
    assert report["safety"]["noIndividualDosing"] is True
    assert report["safety"]["noHomeDetoxPlan"] is True

    assert not list((ROOT / "content" / "addiction").glob("*.b64"))
    assert not (ROOT / "scripts" / "materialize_addiction_condition_guides_v2.py").exists()


def test_conditions_and_audiences_are_linked_and_discoverable() -> None:
    conditions = (ROOT / "addiction" / "conditions" / "index.html").read_text(encoding="utf-8")
    hub = (ROOT / "addiction" / "index.html").read_text(encoding="utf-8")
    for slug in SLUGS:
        assert f"/addiction/{slug}/" in conditions
        assert f"/addiction/{slug}/" in hub
    for audience in AUDIENCES:
        assert f"/addiction/audiences/{audience}/" in hub
    assert "/addiction/conditions/" in hub
    assert "/addiction/methodology/" in hub

    addiction = ET.parse(ROOT / "sitemap-addiction.xml").getroot()
    urls = [node.text for node in addiction.findall("s:url/s:loc", NS)]
    assert len(urls) == len(set(urls))
    assert len(urls) >= 24
    for slug in SLUGS:
        assert f"{BASE_URL}addiction/{slug}/" in urls
    for audience in AUDIENCES:
        assert f"{BASE_URL}addiction/audiences/{audience}/" in urls
    assert f"{BASE_URL}addiction/conditions/" in urls
    assert f"{BASE_URL}addiction/methodology/" in urls

    index = ET.parse(ROOT / "sitemap-index.xml").getroot()
    sitemap_urls = {node.text for node in index.findall("s:sitemap/s:loc", NS)}
    assert f"{BASE_URL}sitemap-addiction.xml" in sitemap_urls
PY

rm -f content/addiction/condition-guides-v2.part00.b64
rm -f content/addiction/condition-guides-v2.part01.b64
rm -f scripts/materialize_addiction_condition_guides_v2.py
rmdir content/addiction 2>/dev/null || true
rm -f .github/addiction-clean-build-trigger.txt

python -m py_compile tests/test_addiction_condition_guides_v2.py
python - <<'PY'
import runpy
namespace = runpy.run_path("tests/test_addiction_condition_guides_v2.py")
tests = [
    value
    for name, value in sorted(namespace.items())
    if name.startswith("test_") and callable(value)
]
assert len(tests) == 2, len(tests)
for test in tests:
    test()
    print(f"PASS {test.__name__}")
PY

git config user.name "healthrenewal-bot"
git config user.email "actions@users.noreply.github.com"
git add -A
git status --short
git commit -m "feat(addiction): publish ten integrated static condition guides"
git push origin "HEAD:${TARGET_BRANCH}"
