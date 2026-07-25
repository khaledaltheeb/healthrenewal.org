from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import expand_v12_direct_core_v235 as core
import lab_source_content_v235 as source

SOURCE_STYLE = """<style data-lab-source-v235-style>
.lab-source-v235{margin-top:2rem;display:grid;gap:1rem}
.lab-source-v235__card{padding:1.25rem;border:1px solid #b9ddd8;border-radius:1.25rem;background:#fff;line-height:1.9}
.lab-source-v235__card h2{line-height:1.45;color:#075f5b}
.lab-source-v235__card li{margin-block:.35rem}
@media print{.lab-source-v235__card{break-inside:avoid}}
</style>"""

for _name in dir(core):
    if not _name.startswith("_"):
        globals().setdefault(_name, getattr(core, _name))


def _seo_visible_head_fragment(definition: dict, kind: str) -> str:
    fragment = source.head_fragment(definition, kind)
    fragment = fragment.replace(
        '<meta data-lab-source-v235-head="twitter-title" name="twitter:title"',
        '<meta name="twitter:title" data-lab-source-v235-head="twitter-title"',
    )
    fragment = fragment.replace(
        '<meta data-lab-source-v235-head="twitter-description" name="twitter:description"',
        '<meta name="twitter:description" data-lab-source-v235-head="twitter-description"',
    )
    return fragment


def _head(definition: dict, kind: str, canonical: str) -> str:
    description = source.rich_description(definition, kind)
    page = core.page_head(definition["title"], description, canonical, definition)
    fragment = _seo_visible_head_fragment(definition, kind)
    return page.replace("</head>", fragment + SOURCE_STYLE + "</head>", 1)


def tool_html(item: dict) -> str:
    canonical = core.url(f"assessment-lab/{item['slug']}/")
    source_box = ""
    if item.get("source"):
        source_box = (
            '<aside class="lab-v12__card"><h2>المصدر والمنهج</h2>'
            f'<p>{core.esc(item["source"])}</p>'
            f'<p><a href="{core.esc(item["source_url"])}" rel="noopener">فتح المصدر الرسمي</a></p></aside>'
        )
    body = source.body_fragment(item, "assessment", core.BASE_PATH)
    return _head(item, "assessment", canonical) + (
        f'<body><main class="lab-v12">{core.nav()}<section class="lab-shell">'
        f'<span class="lab-v12__badge">{core.esc(item["category"])}</span>'
        f'<h1>{core.esc(item["title"])}</h1><p>{core.esc(item["summary"])}</p>'
        f'<p><strong>الفترة:</strong> {core.esc(item.get("period", ""))}</p>'
        f'<div data-v12-lab="assessment" aria-live="polite"></div>{source_box}</section>'
        f'{body}{core.footer()}</main></body></html>'
    )


def game_html(item: dict) -> str:
    canonical = core.url(f"cognitive-lab/{item['slug']}/")
    definition = {
        **item,
        "stages": 5,
        "trials_per_stage": 6,
        "instrument_type": "مهمة تدريبية أصلية غير تشخيصية",
    }
    body = source.body_fragment(definition, "cognitive", core.BASE_PATH)
    return _head(definition, "cognitive", canonical) + (
        f'<body><main class="lab-v12">{core.nav()}<section class="lab-shell">'
        f'<span class="lab-v12__badge">{core.esc(item["category"])}</span>'
        f'<h1>{core.esc(item["title"])}</h1><p>{core.esc(item["summary"])}</p>'
        '<div class="question"><strong>مهم:</strong> النتيجة تدريبية وليست درجة ذكاء سريرية أو تشخيصًا.</div>'
        '<div data-v12-lab="cognitive" aria-live="polite"></div></section>'
        f'{body}{core.footer()}</main></body></html>'
    )


core.tool_html = tool_html
core.game_html = game_html


def main() -> None:
    core.main()
    report_path = core.SITE / "api" / "build-report-v12.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.update(
        {
            "lab_source_content_version": source.VERSION,
            "source_integrated_assessment_pages": len(core.SCALES) + len(core.MONITORS),
            "source_integrated_cognitive_pages": len(core.GAMES),
        }
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "lab_source_content_version": source.VERSION,
                "assessment_pages": report["source_integrated_assessment_pages"],
                "cognitive_pages": report["source_integrated_cognitive_pages"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
