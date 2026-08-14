#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MINIMUM_CHILD_PAGES = 500


def load_publisher(root: Path):
    path = root / 'scripts/publish_research_evidence_learning_v1.py'
    spec = importlib.util.spec_from_file_location('research_evidence_publisher_v1', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load publisher: {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build(repo: Path, site: Path) -> dict[str, object]:
    publisher = load_publisher(repo)
    output = site / 'sections' / 'research-evidence-learning'
    output.mkdir(parents=True, exist_ok=True)

    pages: list[dict[str, str]] = []
    for topic in publisher.TOPICS:
        for intent_slug, intent_title, intent_desc in publisher.INTENTS:
            slug = f'{topic.slug}-{intent_slug}'
            target = output / slug / 'index.html'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                publisher.render_page(topic, intent_slug, intent_title, intent_desc),
                encoding='utf-8',
            )
            pages.append({
                'topic': topic.slug,
                'slug': slug,
                'title': f'{intent_title}: {topic.title}',
                'description': f'{intent_title} في {topic.title}: دليل منهجي عربي لقراءة البحث وتقييم الاستنتاج.',
                'url': f'{publisher.BASE}{slug}/',
            })

    child_count = len(pages)
    if child_count < MINIMUM_CHILD_PAGES:
        raise ValueError(f'only {child_count} child pages; minimum is {MINIMUM_CHILD_PAGES}')
    if len({p['slug'] for p in pages}) != child_count:
        raise ValueError('duplicate slugs')
    if len({p['title'] for p in pages}) != child_count:
        raise ValueError('duplicate titles')
    if len({p['url'] for p in pages}) != child_count:
        raise ValueError('duplicate URLs')

    (output / 'index.html').write_text(publisher.render_hub(pages), encoding='utf-8')
    api = site / 'api'
    api.mkdir(parents=True, exist_ok=True)
    report = {
        'schemaVersion': 2,
        'status': 'base-built',
        'minimumChildPages': MINIMUM_CHILD_PAGES,
        'childPages': child_count,
        'hubPages': 1,
        'totalPages': child_count + 1,
        'topics': len(publisher.TOPICS),
        'intentsPerTopic': len(publisher.INTENTS),
        'uniqueTitles': child_count,
        'uniqueUrls': child_count,
        'sectionUrl': publisher.BASE,
    }
    (api / 'research-evidence-learning-v1.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    print(json.dumps(report, ensure_ascii=False))
    return report


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    site = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    build(repo, site)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
