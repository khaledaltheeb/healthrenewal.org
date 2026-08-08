#!/usr/bin/env python3
from __future__ import annotations

"""Exhaustive, main-first public content recovery.

Production policy:
1. Current ``main`` is authoritative for every path that still exists there.
2. The validated production artifact is a safety net, never a replacement for
   a current-main page.
3. Every reachable Git ref is scanned from repository inception for HTML
   versions. Unique historical editorial fragments are merged into the current
   route instead of replacing it.
4. Missing public pages may be restored from the baseline or Git history.
5. Existing duplicate-consolidation and integrity gates still run afterwards.

The goal is content preservation without allowing an older "richer" page to
silently overwrite a newer canonical page.
"""

import hashlib
import html
import json
import re
import subprocess
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import recover_content_v1 as base
import recover_content_v2 as recovery


_ORIGINAL_SAFE = base.safe

HISTORICAL_RESTORE_BLOCKED_PREFIXES = (
    "professional-assessment-hub/",
    "provider-assessment-platform/",
    "specialists-partners/admin/",
    "specialists-partners/portal/",
)

BLOCK_RE = re.compile(
    r"<(section|article|details|table|blockquote|figure|p|ul|ol)\b[^>]*>.*?</\1\s*>",
    re.I | re.S,
)
ID_RE = re.compile(r'\bid=(["\'])([^"\']+)\1', re.I)
HREF_FRAGMENT_RE = re.compile(r'href=(["\'])#([^"\']+)\1', re.I)
ARIA_REF_RE = re.compile(
    r'\b(aria-labelledby|aria-describedby)=(["\'])([^"\']+)\2', re.I
)

STATS = {
    "historyPathsSeen": 0,
    "historyVersionsSeen": 0,
    "historyUniqueBlobVersions": 0,
    "historyFragmentsMerged": 0,
    "historyPagesEnriched": 0,
    "historyMissingPagesRestored": 0,
    "baselineMissingPagesRestored": 0,
    "mainPagesProtectedFromBaselineReplacement": 0,
    "historySkippedRedirectVersions": 0,
}


def recovery_safe(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return _ORIGINAL_SAFE(path) and not normalized.startswith(HISTORICAL_RESTORE_BLOCKED_PREFIXES)


base.safe = recovery_safe
recovery.b.safe = recovery_safe


def _arg_value(name: str, default: str) -> str:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return default
    if index + 1 >= len(sys.argv):
        return default
    return sys.argv[index + 1]


ROOT = Path(_arg_value("--root", ".")).resolve()


def all_history(_since: str, limit: int = 0) -> dict[str, list[str]]:
    """Return every changed HTML commit per safe path across all reachable refs."""
    output = base.git([
        "log",
        "--all",
        "--no-renames",
        "--diff-filter=AM",
        "--format=@@%H",
        "--name-only",
        "--",
        "*.html",
        "*.htm",
    ])
    current_commit = ""
    commits_by_path: dict[str, list[str]] = defaultdict(list)
    seen_by_path: dict[str, set[str]] = defaultdict(set)

    for line in output.splitlines():
        if line.startswith("@@"):
            current_commit = line[2:].strip()
            continue
        path = line.strip()
        if not current_commit or not path or not recovery_safe(path):
            continue
        if current_commit in seen_by_path[path]:
            continue
        seen_by_path[path].add(current_commit)
        commits_by_path[path].append(current_commit)

    STATS["historyPathsSeen"] = len(commits_by_path)
    STATS["historyVersionsSeen"] = sum(len(values) for values in commits_by_path.values())
    return dict(commits_by_path)


base.history = all_history
recovery.b.history = all_history


class CatFile:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def get(self, commit: str, path: str) -> tuple[str, str] | None:
        if self.proc.stdin is None or self.proc.stdout is None:
            return None
        spec = f"{commit}:{path}\n".encode("utf-8")
        self.proc.stdin.write(spec)
        self.proc.stdin.flush()
        header = self.proc.stdout.readline()
        if not header:
            return None
        if header.rstrip().endswith(b" missing"):
            return None
        parts = header.decode("utf-8", "replace").strip().split()
        if len(parts) < 3 or parts[1] != "blob":
            return None
        object_id = parts[0]
        try:
            size = int(parts[2])
        except ValueError:
            return None
        payload = self.proc.stdout.read(size)
        self.proc.stdout.read(1)
        return object_id, payload.decode("utf-8", "replace")

    def close(self) -> None:
        if self.proc.stdin:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        try:
            self.proc.terminate()
        except OSError:
            pass


def normalized_text(fragment: str) -> str:
    return base.norm(fragment)


def useful_blocks(source: str) -> list[str]:
    result: list[str] = []
    for match in BLOCK_RE.finditer(source):
        block = match.group(0)
        text = normalized_text(block)
        words = base.W.findall(text)
        if len(words) < 18:
            continue
        if len(words) < 45 and any(marker in text for marker in (
            "حقوق النشر",
            "آخر تحديث",
            "المراجعة التالية",
            "هذا المحتوى للتثقيف",
            "لا يغني عن",
            "العودة إلى الرئيسية",
        )):
            continue
        result.append(block)
    return result


def similar_enough(candidate_text: str, known_texts: list[str]) -> bool:
    if not candidate_text:
        return True
    candidate_words = candidate_text.split()
    if len(candidate_words) < 18:
        return True

    for other in known_texts:
        if candidate_text == other:
            return True
        if len(candidate_text) > 80 and candidate_text in other:
            return True
        if len(other) > 80 and other in candidate_text:
            return True

    lower = max(1, int(len(candidate_text) * 0.55))
    upper = int(len(candidate_text) * 1.8) + 1
    for other in known_texts[-160:]:
        if not lower <= len(other) <= upper:
            continue
        if SequenceMatcher(None, candidate_text, other).ratio() >= 0.88:
            return True
    return False


def namespace_ids(block: str, path: str, ordinal: int) -> str:
    """Prevent recovered fragments from introducing duplicate DOM ids."""
    prefix = "hist-" + hashlib.sha1(f"{path}:{ordinal}".encode("utf-8")).hexdigest()[:10]
    mapping: dict[str, str] = {}

    def replace_id(match: re.Match[str]) -> str:
        quote, old = match.group(1), match.group(2)
        new = f"{prefix}-{old}"
        mapping[old] = new
        return f'id={quote}{html.escape(new, quote=True)}{quote}'

    updated = ID_RE.sub(replace_id, block)
    if not mapping:
        return updated

    def replace_href(match: re.Match[str]) -> str:
        quote, old = match.group(1), match.group(2)
        return f'href={quote}#{mapping.get(old, old)}{quote}'

    updated = HREF_FRAGMENT_RE.sub(replace_href, updated)

    def replace_aria(match: re.Match[str]) -> str:
        attr, quote, value = match.group(1), match.group(2), match.group(3)
        mapped = " ".join(mapping.get(token, token) for token in value.split())
        return f"{attr}={quote}{mapped}{quote}"

    return ARIA_REF_RE.sub(replace_aria, updated)


def inject_history(primary: str, path: str, blocks: list[str]) -> str:
    if not blocks:
        return primary
    section_id = "historical-content-" + hashlib.sha1(path.encode()).hexdigest()[:10]
    payload = (
        '\n<section class="historical-content-merge" data-recovery="historical-content-merge-v4" '
        f'aria-labelledby="{section_id}">\n'
        f'<h2 id="{section_id}">محتوى فريد مستعاد من الإصدارات السابقة</h2>\n'
        + "\n".join(blocks)
        + "\n</section>\n"
    )
    lowered = primary.lower()
    for closing in ("</main>", "</article>", "</body>"):
        index = lowered.rfind(closing)
        if index != -1:
            return primary[:index] + payload + primary[index:]
    return primary + payload


def choose_missing_candidate(
    path: str,
    baseline: Path | None,
    versions: list[tuple[str, str, dict]],
) -> tuple[str, str, dict] | None:
    candidates = list(versions)
    if baseline and (baseline / path).is_file():
        text = (baseline / path).read_text(encoding="utf-8", errors="replace")
        metric = base.metrics(path, text)
        if not metric["redirect"]:
            candidates.append(("validated-baseline", text, metric))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item[2]["words"],
            item[2]["score"],
            item[2]["sections"],
            item[2]["bytes"],
        ),
    )


def restore(site: Path, since: str, baseline: Path | None):
    history = all_history(since)
    baseline_paths = (
        {p.relative_to(baseline).as_posix() for p in base.html_files(baseline)}
        if baseline and baseline.exists()
        else set()
    )
    main_paths = {
        p.relative_to(ROOT).as_posix()
        for p in base.html_files(ROOT)
        if recovery_safe(p.relative_to(ROOT).as_posix())
    }

    STATS["mainPagesProtectedFromBaselineReplacement"] = len(main_paths)

    restored: list[dict] = []
    cat = CatFile()
    try:
        all_paths = sorted(main_paths | baseline_paths | set(history))
        for index, path in enumerate(all_paths, 1):
            main_file = ROOT / path
            main_text = (
                main_file.read_text(encoding="utf-8", errors="replace")
                if path in main_paths and main_file.is_file()
                else None
            )

            versions: list[tuple[str, str, dict]] = []
            seen_blobs: set[str] = set()
            for commit in history.get(path, []):
                loaded = cat.get(commit, path)
                if not loaded:
                    continue
                blob_id, text = loaded
                if blob_id in seen_blobs:
                    continue
                seen_blobs.add(blob_id)
                STATS["historyUniqueBlobVersions"] += 1
                metric = base.metrics(path, text)
                if metric["redirect"]:
                    STATS["historySkippedRedirectVersions"] += 1
                    continue
                versions.append((commit, text, metric))

            dst = site / path

            if main_text is None:
                chosen = choose_missing_candidate(path, baseline, versions)
                if chosen is None:
                    continue
                source, primary, metric = chosen
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(primary, encoding="utf-8")
                restored.append({
                    "path": path,
                    "from": source,
                    "previousWords": 0,
                    "restoredWords": metric["words"],
                    "previousScore": 0,
                    "restoredScore": metric["score"],
                    "mode": "restore-missing-only",
                })
                if source == "validated-baseline":
                    STATS["baselineMissingPagesRestored"] += 1
                else:
                    STATS["historyMissingPagesRestored"] += 1
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(main_text, encoding="utf-8")
                primary = main_text

            primary_metric = base.metrics(path, primary)
            if primary_metric["redirect"]:
                continue

            known_texts: list[str] = []
            known_hashes: set[str] = set()
            for block in useful_blocks(primary):
                text = normalized_text(block)
                known_texts.append(text)
                known_hashes.add(hashlib.sha256(text.encode("utf-8")).hexdigest())

            historical_sources: list[tuple[str, str]] = []
            if baseline and (baseline / path).is_file():
                baseline_text = (baseline / path).read_text(encoding="utf-8", errors="replace")
                baseline_metric = base.metrics(path, baseline_text)
                if not baseline_metric["redirect"] and baseline_text != primary:
                    historical_sources.append(("validated-baseline", baseline_text))
            historical_sources.extend((commit, text) for commit, text, _ in versions if text != primary)

            additions: list[str] = []
            merged_sources: set[str] = set()
            ordinal = 0
            for source, historical_text in historical_sources:
                for block in useful_blocks(historical_text):
                    text = normalized_text(block)
                    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    if digest in known_hashes or similar_enough(text, known_texts):
                        continue
                    ordinal += 1
                    additions.append(namespace_ids(block, path, ordinal))
                    known_hashes.add(digest)
                    known_texts.append(text)
                    merged_sources.add(source)

            if additions:
                updated = inject_history(primary, path, additions)
                dst.write_text(updated, encoding="utf-8")
                updated_metric = base.metrics(path, updated)
                STATS["historyFragmentsMerged"] += len(additions)
                STATS["historyPagesEnriched"] += 1
                restored.append({
                    "path": path,
                    "from": sorted(merged_sources),
                    "previousWords": primary_metric["words"],
                    "restoredWords": updated_metric["words"],
                    "previousScore": primary_metric["score"],
                    "restoredScore": updated_metric["score"],
                    "mode": "merge-unique-history-into-main",
                    "uniqueFragmentsMerged": len(additions),
                })

            if index % 250 == 0:
                print(json.dumps({
                    "processed": index,
                    "totalPaths": len(all_paths),
                    "historyPagesEnriched": STATS["historyPagesEnriched"],
                    "missingPagesRestored": (
                        STATS["historyMissingPagesRestored"]
                        + STATS["baselineMissingPagesRestored"]
                    ),
                    "historyFragmentsMerged": STATS["historyFragmentsMerged"],
                }, ensure_ascii=False))
    finally:
        cat.close()

    return restored


recovery.restore = restore


def annotate_report() -> None:
    site = Path(_arg_value("--site", "_site")).resolve()
    report_path = site / "api" / "content-recovery-report.json"
    if not report_path.is_file():
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.update({
        "source": "current main first + validated baseline for missing paths + exhaustive reachable Git history",
        "historySince": "1970-01-01",
        "historyScanMode": "all reachable refs, all safe HTML path revisions, unique blob versions",
        "mainPriorityPolicy": "main always wins for an existing path; history may only add unique editorial fragments",
        "historicalPagesRestored": (
            STATS["historyMissingPagesRestored"] + STATS["baselineMissingPagesRestored"]
        ),
        "historicalPagesEnriched": STATS["historyPagesEnriched"],
        "historicalUniqueFragmentsMerged": STATS["historyFragmentsMerged"],
        "historyPathsSeen": STATS["historyPathsSeen"],
        "historyVersionsSeen": STATS["historyVersionsSeen"],
        "historyUniqueBlobVersions": STATS["historyUniqueBlobVersions"],
        "historySkippedRedirectVersions": STATS["historySkippedRedirectVersions"],
        "baselineMissingPagesRestored": STATS["baselineMissingPagesRestored"],
        "historyMissingPagesRestored": STATS["historyMissingPagesRestored"],
        "mainPagesProtectedFromBaselineReplacement": STATS[
            "mainPagesProtectedFromBaselineReplacement"
        ],
    })
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    recovery.main()
    annotate_report()
