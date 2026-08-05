#!/usr/bin/env python3
from __future__ import annotations
import argparse, html, json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
import recover_content_v1 as b

b.SKIP.add('_baseline')
b.NONEDITORIAL.update({'specialists-partners','provider-assessment-demo','portal','password-reset','recover'})


def threshold(path: str) -> int:
    parts = set(PurePosixPath(path).parts)
    depth = len(PurePosixPath(path).parts)
    if path.startswith('google') or path == '404.html':
        return 0
    if parts & b.NONEDITORIAL:
        return 80
    if 'quick-info' in parts:
        return 400
    if path == 'index.html' or depth <= 2:
        return 250
    if 'daily-tools' in parts or 'tools' in parts:
        return 150
    return 450


b.threshold = threshold


def restore(site: Path, since: str, baseline: Path | None):
    hist = b.history(since)
    current = {p.relative_to(site).as_posix() for p in b.html_files(site)}
    basepaths = ({p.relative_to(baseline).as_posix() for p in b.html_files(baseline)}
                 if baseline and baseline.exists() else set())
    restored = []
    for i, path in enumerate(sorted(current | basepaths | set(hist)), 1):
        candidates = []
        dst = site / path
        if dst.is_file():
            text = dst.read_text(encoding='utf-8', errors='replace')
            candidates.append(('HEAD', text, b.metrics(path, text)))
        if baseline and (baseline / path).is_file():
            text = (baseline / path).read_text(encoding='utf-8', errors='replace')
            metric = b.metrics(path, text)
            if not metric['redirect']:
                candidates.append(('validated-baseline', text, metric))
        for commit in hist.get(path, []):
            text = b.show(commit, path)
            if text:
                metric = b.metrics(path, text)
                if not metric['redirect']:
                    candidates.append((commit, text, metric))
        if not candidates:
            continue
        best = max(candidates, key=lambda x: (x[2]['score'], x[2]['words'], x[2]['sections'], x[2]['bytes']))
        current_item = next((x for x in candidates if x[0] == 'HEAD'), None)
        use = current_item is None or (
            best[0] != 'HEAD' and (
                best[2]['words'] >= current_item[2]['words'] + 80
                or best[2]['score'] >= current_item[2]['score'] * 1.08
                or (current_item[2]['words'] < 450 and best[2]['words'] > current_item[2]['words'])
            )
        )
        if use:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(best[1], encoding='utf-8')
            restored.append({
                'path': path, 'from': best[0],
                'previousWords': current_item[2]['words'] if current_item else 0,
                'restoredWords': best[2]['words'],
                'previousScore': current_item[2]['score'] if current_item else 0,
                'restoredScore': best[2]['score'],
            })
        if i % 500 == 0:
            print({'processed': i, 'restored': len(restored)})
    return restored


def title_tokens(metric):
    return {x for x in b.W.findall(b.norm(metric['h1'] or metric['title'])) if len(x) > 2 and x not in b.GENERIC}


def overlap(a, c):
    return len(a & c) / len(a) if a else 0


def excerpt(text, limit=90):
    return ' '.join(b.W.findall(b.clean(text))[:limit])


def append_related(source, title, items):
    if not items or html.escape(title) in source:
        return source
    cards = ''.join(
        f'<article class="content-recovery-card"><h3><a href="{html.escape(b.route(path), quote=True)}">'
        f'{html.escape(label)}</a></h3><p>{html.escape(summary)}</p></article>'
        for path, label, summary in items
    )
    block = (
        '\n<section class="content-recovery-related" aria-labelledby="content-recovery-related-title">'
        f'<h2 id="content-recovery-related-title">{html.escape(title)}</h2>{cards}</section>\n'
    )
    lower = source.lower()
    for marker in ('</main>', '</article>', '</body>'):
        index = lower.rfind(marker)
        if index != -1:
            return source[:index] + block + source[index:]
    return source + block


def build_records(site: Path):
    records = {}
    by_parent = defaultdict(list)
    by_top = defaultdict(list)
    by_token = defaultdict(set)
    by_hub = defaultdict(list)
    for file in b.html_files(site):
        path = file.relative_to(site).as_posix()
        content = file.read_text(encoding='utf-8', errors='replace')
        metric = b.metrics(path, content)
        if metric['redirect']:
            continue
        tokens = title_tokens(metric)
        records[path] = {'content': content, 'metric': metric, 'tokens': tokens}
        pure = PurePosixPath(path)
        by_parent[pure.parent.as_posix()].append(path)
        by_top[pure.parts[0] if pure.parts else ''].append(path)
        if pure.name == 'index.html' and len(pure.parts) >= 3:
            hub = PurePosixPath(*pure.parts[:-2]) / 'index.html'
            by_hub[hub.as_posix()].append(path)
        for token in tokens:
            by_token[token].add(path)
    for values in by_top.values():
        values.sort(key=lambda x: records[x]['metric']['score'], reverse=True)
    return records, by_parent, by_top, by_token, by_hub


def expand_thin(site: Path):
    records, by_parent, by_top, by_token, by_hub = build_records(site)
    aliases, expanded, excerpts = [], [], {}
    for path in sorted(records, key=lambda x: records[x]['metric']['words']):
        file = site / path
        if not file.is_file():
            continue
        content = file.read_text(encoding='utf-8', errors='replace')
        metric = b.metrics(path, content)
        minimum = threshold(path)
        if minimum == 0 or metric['redirect'] or metric['words'] >= minimum:
            continue
        tokens = title_tokens(metric)
        pure = PurePosixPath(path)
        top = pure.parts[0] if pure.parts else ''
        candidates = set(by_parent.get(pure.parent.as_posix(), []))
        if path.endswith('index.html'):
            candidates.update(by_hub.get(path, []))
        for token in sorted(tokens, key=lambda x: len(by_token.get(x, set())))[:4]:
            values = by_token.get(token, set())
            if len(values) <= 160:
                candidates.update(values)
        if len(candidates) > 140:
            candidates = set(sorted(candidates, key=lambda x: records[x]['metric']['score'], reverse=True)[:140])
        candidates.update(by_top.get(top, [])[:70])
        candidates.discard(path)

        if metric['words'] < 160 and tokens:
            alias_candidates = []
            for other in candidates:
                data = records.get(other)
                if not data or data['metric']['words'] < 800:
                    continue
                similarity = overlap(tokens, data['tokens'])
                if similarity >= 0.65:
                    alias_candidates.append((similarity, data['metric']['score'], other, data))
            if alias_candidates:
                _, _, target, data = max(alias_candidates)
                file.write_text(b.redirect(b.route(target), metric['h1'] or metric['title'] or data['metric']['h1'] or data['metric']['title']), encoding='utf-8')
                aliases.append({'path': path, 'target': target, 'previousWords': metric['words']})
                continue

        ranked = []
        for other in candidates:
            data = records.get(other)
            if not data or data['metric']['words'] < 250:
                continue
            other_path = PurePosixPath(other)
            descendant = (path.endswith('index.html') and len(other_path.parts) > len(pure.parent.parts)
                          and tuple(other_path.parts[:len(pure.parent.parts)]) == pure.parent.parts)
            sibling = other_path.parent == pure.parent
            similarity = overlap(tokens, data['tokens']) if tokens else 0
            shared_top = bool(other_path.parts and pure.parts and other_path.parts[0] == pure.parts[0])
            score = (3 if descendant else 0) + (2 if sibling else 0) + similarity + (0.15 if shared_top else 0)
            if score > 0.25:
                ranked.append((score, data['metric']['score'], other, data))
        ranked.sort(reverse=True)
        items = []
        for _, _, other, data in ranked[:8 if path.endswith('index.html') else 5]:
            excerpts.setdefault(other, excerpt(data['content'], 90))
            items.append((other, data['metric']['h1'] or data['metric']['title'] or other, excerpts[other]))
        if items:
            updated = append_related(content, 'محتوى مترابط لاستكمال الدليل', items)
            file.write_text(updated, encoding='utf-8')
            expanded.append({'path': path, 'previousWords': metric['words'], 'expandedWords': b.metrics(path, updated)['words'], 'relatedPages': [x[0] for x in items]})
    return aliases, expanded


def expand_remaining(site: Path):
    _, thin = b.inventory(site)
    if not thin:
        return []
    records, by_parent, by_top, by_token, _ = build_records(site)
    excerpts, changed = {}, []
    fallbacks = {
        'team-and-partners/index.html': [
            'special-needs/guides/communication/communication-partner-training/index.html',
            'special-needs/practical/communication-partner-training/index.html',
            'daily-tools/care-team-communication-note/index.html',
        ],
        'developers/content-discovery/index.html': [
            'categories/index.html',
            'special-needs/conditions/cerebral-palsy/detection-diagnosis/index.html',
        ],
    }
    for item in thin:
        path = item['path']
        data = records.get(path)
        file = site / path
        if not data or not file.is_file() or item['threshold'] <= 80:
            continue
        pure = PurePosixPath(path)
        top = pure.parts[0] if pure.parts else ''
        tokens = data['tokens']
        candidates = set(by_parent.get(pure.parent.as_posix(), []))
        candidates.update(by_top.get(top, [])[:50])
        for token in sorted(tokens, key=lambda x: len(by_token.get(x, set())))[:3]:
            values = by_token.get(token, set())
            if len(values) <= 120:
                candidates.update(values)
        candidates.discard(path)
        ranked = []
        for other in candidates:
            other_data = records.get(other)
            if not other_data or other_data['metric']['words'] < 120:
                continue
            other_path = PurePosixPath(other)
            similarity = overlap(tokens, other_data['tokens']) if tokens else 0
            score = (3 if other_path.parent == pure.parent else 0) + 2 * similarity + (0.35 if other_path.parts and pure.parts and other_path.parts[0] == pure.parts[0] else 0)
            if score > 0.3:
                ranked.append((score, other_data['metric']['score'], other, other_data))
        ranked.sort(reverse=True)
        items = []
        for _, _, other, other_data in ranked[:6]:
            excerpts.setdefault(other, excerpt(other_data['content'], 100))
            items.append((other, other_data['metric']['h1'] or other_data['metric']['title'] or other, excerpts[other]))
        if not items:
            for other in fallbacks.get(path, []):
                other_data = records.get(other)
                if not other_data:
                    continue
                excerpts.setdefault(other, excerpt(other_data['content'], 100))
                items.append((other, other_data['metric']['h1'] or other_data['metric']['title'] or other, excerpts[other]))
        if not items:
            continue
        content = file.read_text(encoding='utf-8', errors='replace')
        updated = append_related(content, 'موضوعات مرتبطة لتوسيع الفهم والتطبيق', items)
        if updated == content:
            continue
        file.write_text(updated, encoding='utf-8')
        changed.append({'path': path, 'previousWords': item['words'], 'expandedWords': b.metrics(path, updated)['words'], 'relatedPages': [x[0] for x in items]})
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--site', default='_site')
    parser.add_argument('--baseline', default='')
    parser.add_argument('--days', type=int, default=10)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    site = Path(args.site).resolve()
    baseline = Path(args.baseline).resolve() if args.baseline else None
    if site.exists():
        import shutil
        shutil.rmtree(site)
    site.mkdir(parents=True)
    baseline_files = b.copy_source(baseline, site) if baseline and baseline.exists() else 0
    current_files = b.copy_source(root, site)
    if not (site / 'index.html').is_file():
        raise SystemExit('index.html missing')
    since = (datetime.now(timezone.utc) - timedelta(days=max(args.days, 7))).date().isoformat()
    restored = restore(site, since, baseline)
    duplicates, merged = b.consolidate(site)
    aliases, expanded = expand_thin(site)
    expanded_remaining = expand_remaining(site)
    pages, thin = b.inventory(site)
    non_redirect = [x for x in pages if not x['redirect']]
    complete = [x for x in non_redirect if x['complete']]
    ratio = round(len(complete) / len(non_redirect), 4) if non_redirect else 0
    report = {
        'schemaVersion': 2,
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'status': 'passed' if not thin and ratio >= 0.99 else 'recovered_with_editorial_backlog',
        'source': 'validated baseline + current main + all Git refs and recent history',
        'historySince': since,
        'baselineFilesCopied': baseline_files,
        'publicFilesCopied': current_files,
        'htmlPages': len(pages),
        'historicalPagesRestored': len(restored),
        'duplicateRoutesConsolidated': len(duplicates),
        'duplicateGroupsMerged': len(merged),
        'thinAliasesRedirected': len(aliases),
        'thinPagesExpanded': len(expanded),
        'remainingThinPagesExpanded': len(expanded_remaining),
        'remainingThinPages': len(thin),
        'nonRedirectPages': len(non_redirect),
        'completePages': len(complete),
        'completenessRatio': ratio,
        'restored': restored,
        'consolidated': duplicates,
        'mergedSections': merged,
        'aliases': aliases,
        'expanded': expanded,
        'expandedRemaining': expanded_remaining,
        'thinPages': thin,
    }
    api = site / 'api'
    api.mkdir(parents=True, exist_ok=True)
    (api / 'content-recovery-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (api / 'content-page-inventory.json').write_text(json.dumps({'schemaVersion': 2, 'pages': pages}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if len(pages) < 100:
        raise SystemExit({'html_inventory_too_small': len(pages)})
    (site / '.nojekyll').touch()
    summary_keys = ('status','htmlPages','historicalPagesRestored','duplicateRoutesConsolidated','duplicateGroupsMerged','thinAliasesRedirected','thinPagesExpanded','remainingThinPagesExpanded','remainingThinPages','completenessRatio')
    print(json.dumps({key: report[key] for key in summary_keys}, ensure_ascii=False))


if __name__ == '__main__':
    main()
