#!/usr/bin/env python3
"""Exhaustive, read-only archaeology for historical Health Renewal repository bundles.

The audit deliberately does NOT publish historical payloads. It reconstructs split
Base64/gzip bundles in memory, inventories embedded members, compares recoverable
web routes against the current repository and a validated production artifact, and
emits machine-readable candidate reports for deliberate recovery.
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import io
import json
import os
import re
import tarfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator

HISTORICAL_NAME_RE = re.compile(
    r"^\.(?:.*(?:bundle|release|archive|final|report|validation|verification|mr\d+|v\d+|phase\d+|search|catalog|home|library|content|condition|intervention|workflow|layout|site|pages|automation|ingestion|fdi|sss).*)$",
    re.I,
)
PART_RE = re.compile(r"^(?P<prefix>.*?)(?:\.part|part)(?P<num>\d+)$", re.I)
WEB_EXTS = {".html", ".htm"}
TEXT_EXTS = {".html", ".htm", ".md", ".markdown", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".xml", ".yml", ".yaml", ".py", ".js", ".css"}
IGNORE_ROOTS = {".git", ".github", ".idea", ".vscode", ".venv", "node_modules", "_site"}
MAX_BUNDLE_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 64 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean_rel(path: str) -> str:
    path = path.replace("\\", "/").lstrip("./")
    while "//" in path:
        path = path.replace("//", "/")
    return path


def route_from_path(path: str) -> str | None:
    p = clean_rel(path)
    if not p.lower().endswith((".html", ".htm")):
        return None
    if p.endswith("/index.html"):
        route = "/" + p[: -len("index.html")]
    elif p == "index.html":
        route = "/"
    else:
        route = "/" + re.sub(r"\.(?:html?|HTML?)$", "", p) + "/"
    route = re.sub(r"/+", "/", route)
    return route


def normalized_text_fingerprint(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return sha256(text.encode("utf-8"))


def extract_title(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    match = re.search(r"<title\b[^>]*>(.*?)</title>", text, flags=re.I | re.S)
    if not match:
        match = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, flags=re.I | re.S)
    if not match:
        return ""
    value = re.sub(r"<[^>]+>", " ", match.group(1))
    return re.sub(r"\s+", " ", value).strip()[:300]


def text_word_count(data: bytes) -> int:
    text = data.decode("utf-8", errors="replace")
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return len(re.findall(r"[\w\u0600-\u06FF]+", text, flags=re.UNICODE))


def iter_regular_files(root: Path) -> Iterator[Path]:
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_ROOTS]
        base_path = Path(base)
        for name in files:
            p = base_path / name
            if p.is_file():
                yield p


def historical_roots(repo: Path) -> list[Path]:
    roots: list[Path] = []
    for p in repo.iterdir():
        if not p.is_dir() or p.name in IGNORE_ROOTS:
            continue
        if HISTORICAL_NAME_RE.match(p.name):
            roots.append(p)
    return sorted(roots, key=lambda p: p.name.lower())


def split_groups(root: Path) -> list[list[Path]]:
    groups: dict[tuple[str, str], list[tuple[int, Path]]] = defaultdict(list)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        m = PART_RE.match(p.name)
        if not m:
            continue
        groups[(str(p.parent.relative_to(root)), m.group("prefix"))].append((int(m.group("num")), p))
    result: list[list[Path]] = []
    for items in groups.values():
        nums = sorted(n for n, _ in items)
        if not nums or nums[0] != 0 or nums != list(range(nums[-1] + 1)):
            continue
        result.append([p for _, p in sorted(items)])
    return result


def decode_split_payload(parts: list[Path]) -> tuple[bytes | None, str, str | None]:
    try:
        raw = b"".join(p.read_bytes().strip() for p in parts)
        if len(raw) > MAX_BUNDLE_BYTES:
            return None, "too_large", f"encoded payload exceeds {MAX_BUNDLE_BYTES} bytes"
        compact = re.sub(rb"\s+", b"", raw)
        try:
            decoded = base64.b64decode(compact, validate=True)
            encoding = "base64"
        except Exception:
            decoded = raw
            encoding = "raw"
        if decoded.startswith(b"\x1f\x8b"):
            decoded = gzip.decompress(decoded)
            encoding += "+gzip"
        if len(decoded) > MAX_BUNDLE_BYTES:
            return None, encoding, f"decoded payload exceeds {MAX_BUNDLE_BYTES} bytes"
        return decoded, encoding, None
    except Exception as exc:
        return None, "error", f"{type(exc).__name__}: {exc}"


def safe_member_name(name: str) -> str | None:
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts:
        return None
    value = str(p).lstrip("./")
    return value or None


def payload_members(payload: bytes, source_label: str) -> tuple[list[tuple[str, bytes]], str]:
    members: list[tuple[str, bytes]] = []
    bio = io.BytesIO(payload)
    try:
        if tarfile.is_tarfile(bio):
            bio.seek(0)
            with tarfile.open(fileobj=bio, mode="r:*") as tf:
                for member in tf.getmembers():
                    if not member.isfile() or member.size > MAX_MEMBER_BYTES:
                        continue
                    name = safe_member_name(member.name)
                    if not name:
                        continue
                    extracted = tf.extractfile(member)
                    if extracted is None:
                        continue
                    members.append((name, extracted.read(MAX_MEMBER_BYTES + 1)[:MAX_MEMBER_BYTES]))
            return members, "tar"
    except Exception:
        pass
    bio.seek(0)
    try:
        if zipfile.is_zipfile(bio):
            bio.seek(0)
            with zipfile.ZipFile(bio) as zf:
                for info in zf.infolist():
                    if info.is_dir() or info.file_size > MAX_MEMBER_BYTES:
                        continue
                    name = safe_member_name(info.filename)
                    if not name:
                        continue
                    members.append((name, zf.read(info)[:MAX_MEMBER_BYTES]))
            return members, "zip"
    except Exception:
        pass
    return [(source_label, payload)], "single"


@dataclass
class WebEntry:
    source_root: str
    source_container: str
    member_path: str
    route: str
    bytes: int
    sha256: str
    text_fingerprint: str
    title: str
    words: int


def inventory_web_entry(source_root: str, source_container: str, member_path: str, data: bytes) -> WebEntry | None:
    route = route_from_path(member_path)
    if route is None:
        return None
    return WebEntry(
        source_root=source_root,
        source_container=source_container,
        member_path=clean_rel(member_path),
        route=route,
        bytes=len(data),
        sha256=sha256(data),
        text_fingerprint=normalized_text_fingerprint(data),
        title=extract_title(data),
        words=text_word_count(data),
    )


def current_route_map(root: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not root.exists():
        return result
    for p in root.rglob("*.html"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        route = route_from_path(rel)
        if route is None:
            continue
        data = p.read_bytes()
        result[route] = {
            "path": rel,
            "sha256": sha256(data),
            "text_fingerprint": normalized_text_fingerprint(data),
            "words": text_word_count(data),
            "title": extract_title(data),
        }
    return result


def classify(entry: WebEntry, repo_map: dict[str, dict], prod_map: dict[str, dict]) -> tuple[str, dict | None]:
    peer = prod_map.get(entry.route) or repo_map.get(entry.route)
    if peer is None:
        return "historical_only_route", None
    if entry.sha256 == peer["sha256"]:
        return "exact_duplicate", peer
    if entry.text_fingerprint == peer["text_fingerprint"]:
        return "content_equivalent", peer
    if entry.words > peer.get("words", 0) + max(100, int(peer.get("words", 0) * 0.15)):
        return "historical_richer_same_route", peer
    return "different_same_route", peer


def candidate_score(entry: WebEntry, classification: str, peer: dict | None) -> int:
    score = min(entry.words, 5000)
    if classification == "historical_only_route":
        score += 6000
    elif classification == "historical_richer_same_route":
        score += 3500
        if peer:
            score += max(0, entry.words - peer.get("words", 0))
    if entry.title:
        score += 250
    if entry.words < 250:
        score -= 4000
    return score


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--production", default="/tmp/validated-production")
    ap.add_argument("--out", default="historical-audit")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    prod = Path(args.production).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    roots = historical_roots(repo)
    repo_map = current_route_map(repo)
    prod_map = current_route_map(prod)
    root_reports: list[dict] = []
    web_entries: list[WebEntry] = []
    payload_errors: list[dict] = []
    bundle_member_exts: Counter[str] = Counter()
    bundle_member_count = 0

    for root in roots:
        all_files = [p for p in root.rglob("*") if p.is_file()]
        groups = split_groups(root)
        grouped_paths = {p.resolve() for group in groups for p in group}
        decoded_groups = 0
        decoded_members = 0
        decoded_web = 0

        for group in groups:
            payload, encoding, error = decode_split_payload(group)
            label = f"{root.name}/{' + '.join(p.name for p in group[:2])}{'...' if len(group) > 2 else ''}"
            if payload is None:
                payload_errors.append({"root": root.name, "container": label, "encoding": encoding, "error": error})
                continue
            members, payload_type = payload_members(payload, group[0].stem)
            decoded_groups += 1
            decoded_members += len(members)
            bundle_member_count += len(members)
            for member_name, data in members:
                ext = Path(member_name).suffix.lower() or "[none]"
                bundle_member_exts[ext] += 1
                entry = inventory_web_entry(root.name, f"split:{payload_type}:{encoding}", member_name, data)
                if entry:
                    web_entries.append(entry)
                    decoded_web += 1

        direct_web = 0
        for p in all_files:
            if p.resolve() in grouped_paths:
                continue
            if p.suffix.lower() not in WEB_EXTS:
                continue
            try:
                data = p.read_bytes()
            except OSError:
                continue
            entry = inventory_web_entry(root.name, "direct", p.relative_to(root).as_posix(), data)
            if entry:
                web_entries.append(entry)
                direct_web += 1

        ext_counts = Counter((p.suffix.lower() or "[none]") for p in all_files)
        root_reports.append({
            "root": root.name,
            "files": len(all_files),
            "bytes": sum(p.stat().st_size for p in all_files),
            "extensions": dict(ext_counts.most_common()),
            "splitGroups": len(groups),
            "decodedGroups": decoded_groups,
            "decodedMembers": decoded_members,
            "decodedWebPages": decoded_web,
            "directWebPages": direct_web,
        })

    classifications = Counter()
    rows: list[dict] = []
    by_route: dict[str, list[dict]] = defaultdict(list)
    for entry in web_entries:
        cls, peer = classify(entry, repo_map, prod_map)
        classifications[cls] += 1
        row = asdict(entry)
        row["classification"] = cls
        row["current_words"] = peer.get("words", 0) if peer else 0
        row["current_path"] = peer.get("path", "") if peer else ""
        row["score"] = candidate_score(entry, cls, peer)
        rows.append(row)
        by_route[entry.route].append(row)

    # Deduplicate candidate list by route, retaining the strongest historical version.
    candidate_classes = {"historical_only_route", "historical_richer_same_route"}
    candidates: list[dict] = []
    for route, versions in by_route.items():
        eligible = [v for v in versions if v["classification"] in candidate_classes]
        if not eligible:
            continue
        best = max(eligible, key=lambda v: (v["score"], v["words"], v["bytes"]))
        best = dict(best)
        best["historical_versions"] = len(versions)
        best["historical_roots"] = sorted({v["source_root"] for v in versions})
        candidates.append(best)
    candidates.sort(key=lambda r: (-r["score"], -r["words"], r["route"]))

    duplicate_hashes = Counter(e.sha256 for e in web_entries)
    duplicate_text = Counter(e.text_fingerprint for e in web_entries)
    summary = {
        "schemaVersion": 1,
        "status": "passed",
        "policy": "read-only archaeology; historical payloads are never auto-published",
        "repository": str(repo),
        "productionArtifact": str(prod),
        "historicalRootCount": len(roots),
        "historicalRoots": [p.name for p in roots],
        "currentRepositoryRoutes": len(repo_map),
        "validatedProductionRoutes": len(prod_map),
        "historicalWebVersions": len(web_entries),
        "historicalUniqueRoutes": len(by_route),
        "classifications": dict(classifications),
        "recoveryCandidateRoutes": len(candidates),
        "splitBundleMemberCount": bundle_member_count,
        "splitBundleMemberExtensions": dict(bundle_member_exts.most_common()),
        "payloadErrors": len(payload_errors),
        "exactDuplicatePayloadGroups": sum(1 for n in duplicate_hashes.values() if n > 1),
        "contentDuplicateGroups": sum(1 for n in duplicate_text.values() if n > 1),
        "roots": root_reports,
        "topCandidates": candidates[:100],
    }

    (out / "historical-repository-audit-v1.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "historical-payload-errors-v1.json").write_text(json.dumps(payload_errors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "historical-recovery-candidates-v1.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fields = ["score", "classification", "route", "title", "words", "current_words", "bytes", "source_root", "source_container", "member_path", "historical_versions", "historical_roots", "sha256", "text_fingerprint", "current_path"]
    with (out / "historical-recovery-candidates-v1.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in candidates:
            item = dict(row)
            item["historical_roots"] = " | ".join(item.get("historical_roots", []))
            writer.writerow(item)

    with (out / "historical-web-versions-v1.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        fields2 = ["classification", "route", "title", "words", "current_words", "bytes", "source_root", "source_container", "member_path", "score", "sha256", "text_fingerprint", "current_path"]
        writer = csv.DictWriter(fh, fieldnames=fields2, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["route"], -r["words"])))

    print(json.dumps({k: summary[k] for k in ["status", "historicalRootCount", "currentRepositoryRoutes", "validatedProductionRoutes", "historicalWebVersions", "historicalUniqueRoutes", "classifications", "recoveryCandidateRoutes", "splitBundleMemberCount", "payloadErrors"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
