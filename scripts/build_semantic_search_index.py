#!/usr/bin/env python3
"""Build a browser-readable semantic search index for the static site.

The builder extracts meaningful Arabic text from HTML files, chunks it, embeds
passages with intfloat/multilingual-e5-small, and writes sharded JSON metadata
plus normalized float16 vectors for client-side cosine similarity search.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Iterator
from urllib.parse import urljoin, urlparse

import numpy as np
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "fd1525a9fd15316a2d503bf26ab031a61d056e98"
BROWSER_MODEL_ID = "Xenova/multilingual-e5-small"
BROWSER_MODEL_REVISION = "761b726dd34fb83930e26aab4e9ac3899aa1fa78"
BASE_URL = "https://healthrenewal.org/"
LEGACY_BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"
DIMENSIONS = 384
DEFAULT_CHUNK_CHARS = 900
DEFAULT_OVERLAP_CHARS = 140
DEFAULT_SHARD_SIZE = 1500

EXCLUDED_PARTS = {
    ".git",
    ".github",
    "node_modules",
    "tests",
    "scripts",
    "ai-search",
    "admin",
    "portal",
    "account",
}
EXCLUDED_FILES = {"404.html", "contact.html", "professional-console.html"}
REMOVABLE_TAGS = {
    "script",
    "style",
    "svg",
    "canvas",
    "template",
    "noscript",
    "nav",
    "header",
    "footer",
    "form",
    "button",
}
TEXT_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "td", "th", "blockquote", "dd", "dt"}
WHITESPACE_RE = re.compile(r"\s+")

SECTION_LABELS = {
    "encyclopedia": "الموسوعة النفسية",
    "special-needs": "ذوو الاحتياجات الخاصة",
    "family-guide": "دليل الأسرة",
    "comparisons": "المقارنات",
    "magazine": "المجلة والأبحاث",
    "library": "المكتبة",
    "care-guides": "أدلة التعامل",
    "daily-tools": "الأدوات اليومية",
    "assessments": "المقاييس والتقييم",
    "sectors": "القطاعات",
    "tips": "النصائح",
    "learning-paths": "مسارات التعلم",
}


@dataclass(slots=True)
class Chunk:
    id: str
    title: str
    section: str
    sectionKey: str
    heading: str
    url: str
    audience: list[str]
    excerpt: str
    text: str
    sourcePath: str


def clean_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value or "").strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def should_index(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if path.name in EXCLUDED_FILES:
        return False
    if any(part in EXCLUDED_PARTS or part.startswith(".") for part in relative.parts[:-1]):
        return False
    return path.suffix.lower() == ".html"


def canonical_url(soup: BeautifulSoup, relative_path: Path) -> str:
    clean_path = relative_path.as_posix()
    if clean_path.endswith("index.html"):
        clean_path = clean_path[: -len("index.html")]

    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    href = str(canonical.get("href") or "").strip() if canonical else ""
    candidate = urljoin(BASE_URL, href or clean_path)

    if candidate.startswith(LEGACY_BASE_URL):
        candidate = urljoin(BASE_URL, candidate[len(LEGACY_BASE_URL):])

    parsed = urlparse(candidate)
    if parsed.netloc == "www.healthrenewal.org":
        candidate = parsed._replace(netloc="healthrenewal.org").geturl()
        parsed = urlparse(candidate)

    if parsed.scheme != "https" or parsed.netloc != "healthrenewal.org":
        candidate = urljoin(BASE_URL, clean_path)

    parsed = urlparse(candidate)
    return parsed._replace(query="", fragment="").geturl()


def infer_section(relative_path: Path) -> tuple[str, str]:
    parts = relative_path.parts
    key = parts[0] if len(parts) > 1 else "home"
    return key, SECTION_LABELS.get(key, "المنصة")


def infer_audience(relative_path: Path, text: str) -> list[str]:
    haystack = f"{relative_path.as_posix()} {text}".lower()
    audiences: set[str] = set()
    if any(term in haystack for term in ("family", "caregiver", "الأسرة", "الاهل", "الأهل", "مقدم الرعاية")):
        audiences.add("family")
    if any(term in haystack for term in ("professional", "provider", "specialist", "المختص", "مقدم الخدمة", "المعالج")):
        audiences.add("professional")
    if any(term in haystack for term in ("research", "library", "magazine", "student", "الباحث", "الطالب", "الدراسة")):
        audiences.add("student")
    if not audiences:
        audiences.add("general")
    return sorted(audiences)


def extract_page_blocks(path: Path, root: Path) -> tuple[str, str, str, list[tuple[str, str]]]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")

    robots = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    if robots and "noindex" in str(robots.get("content", "")).lower():
        return "", "", "", []

    for tag_name in REMOVABLE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = clean_text(title_tag.get_text(" ", strip=True) if title_tag else path.stem)
    url = canonical_url(soup, path.relative_to(root))

    blocks: list[tuple[str, str]] = []
    current_heading = title
    main = soup.find("main") or soup.find("article") or soup.body or soup
    visible_text = clean_text(main.get_text(" ", strip=True))
    for element in main.find_all(list(TEXT_TAGS)):
        text = clean_text(element.get_text(" ", strip=True))
        if not text:
            continue
        if element.name in {"h1", "h2", "h3", "h4"}:
            current_heading = text
            continue
        if len(text) >= 35:
            blocks.append((current_heading, text))

    return title, url, visible_text, blocks


def split_long_text(text: str, max_chars: int, overlap: int) -> Iterator[str]:
    text = clean_text(text)
    if len(text) <= max_chars:
        if text:
            yield text
        return

    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind("، ", start, end), text.rfind("؛ ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunk = clean_text(text[start:end])
        if chunk:
            yield chunk
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)


def chunk_blocks(
    title: str,
    blocks: list[tuple[str, str]],
    max_chars: int,
    overlap: int,
) -> Iterator[tuple[str, str]]:
    current_heading = title
    buffer: list[str] = []
    size = 0

    def flush() -> Iterator[tuple[str, str]]:
        nonlocal buffer, size
        if buffer:
            joined = clean_text(" ".join(buffer))
            if joined:
                yield current_heading, joined
            tail = joined[-overlap:] if overlap and len(joined) > overlap else ""
            buffer = [tail] if tail else []
            size = len(tail)

    for heading, text in blocks:
        if heading != current_heading and buffer:
            yield from flush()
            current_heading = heading
        elif heading != current_heading:
            current_heading = heading

        for piece in split_long_text(text, max_chars, overlap):
            projected = size + len(piece) + 1
            if buffer and projected > max_chars:
                yield from flush()
            buffer.append(piece)
            size += len(piece) + 1

    if buffer:
        joined = clean_text(" ".join(buffer))
        if joined:
            yield current_heading, joined


def collect_chunks(root: Path, max_chars: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen_hashes: set[str] = set()

    html_files = sorted(path for path in root.rglob("*.html") if should_index(path, root))
    for path in html_files:
        title, url, page_text, blocks = extract_page_blocks(path, root)
        if not title or not blocks:
            continue

        relative_path = path.relative_to(root)
        section_key, section_label = infer_section(relative_path)
        audience = infer_audience(relative_path, page_text)

        for ordinal, (heading, text) in enumerate(chunk_blocks(title, blocks, max_chars, overlap), start=1):
            enriched = clean_text(f"{title}. {heading}. {text}")
            if len(enriched) < 120:
                continue
            content_hash = sha256_bytes(enriched.encode("utf-8"))
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)

            chunk_id = f"{sha256_bytes(str(relative_path).encode())[:12]}-{ordinal:03d}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    title=title,
                    section=section_label,
                    sectionKey=section_key,
                    heading=heading,
                    url=url,
                    audience=audience,
                    excerpt=text[:320].rstrip() + ("…" if len(text) > 320 else ""),
                    text=enriched,
                    sourcePath=relative_path.as_posix(),
                )
            )

    return chunks


def write_json(path: Path, payload: object) -> bytes:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(data)
    return data


def remove_old_artifacts(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for pattern in ("shard-*.meta.json", "shard-*.f16.bin", "shard-*.f16.json"):
        for path in output.glob(pattern):
            path.unlink()


def build_index(args: argparse.Namespace) -> dict[str, object]:
    root = args.root.resolve()
    output = args.output.resolve()
    remove_old_artifacts(output)

    chunks = collect_chunks(root, args.chunk_chars, args.overlap_chars)
    if not chunks:
        raise RuntimeError("No indexable HTML content was found")

    print(f"Collected {len(chunks):,} unique chunks", flush=True)
    model = SentenceTransformer(MODEL_ID, revision=MODEL_REVISION)
    passages = [f"passage: {chunk.text}" for chunk in chunks]
    embeddings = model.encode(
        passages,
        batch_size=args.batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    if embeddings.ndim != 2 or embeddings.shape[1] != DIMENSIONS:
        raise RuntimeError(f"Unexpected embedding shape: {embeddings.shape}")

    embeddings = np.asarray(embeddings, dtype="<f2")
    shards: list[dict[str, object]] = []

    for shard_number, start in enumerate(range(0, len(chunks), args.shard_size)):
        end = min(len(chunks), start + args.shard_size)
        metadata_name = f"shard-{shard_number:03d}.meta.json"
        embeddings_name = f"shard-{shard_number:03d}.f16.bin"
        embeddings_json_name = f"shard-{shard_number:03d}.f16.json"
        metadata_path = output / metadata_name
        embeddings_path = output / embeddings_name
        embeddings_json_path = output / embeddings_json_name

        metadata_payload = [asdict(chunk) for chunk in chunks[start:end]]
        metadata_bytes = write_json(metadata_path, metadata_payload)
        shard_vectors = embeddings[start:end]
        shard_vectors.tofile(embeddings_path)
        vector_bytes = embeddings_path.read_bytes()
        vector_sha256 = sha256_bytes(vector_bytes)
        embeddings_json_bytes = write_json(
            embeddings_json_path,
            {
                "version": 1,
                "encoding": "base64",
                "dtype": "float16",
                "endianness": "little",
                "dimensions": DIMENSIONS,
                "count": end - start,
                "byteLength": len(vector_bytes),
                "sha256": vector_sha256,
                "data": base64.b64encode(vector_bytes).decode("ascii"),
            },
        )

        shards.append(
            {
                "metadata": metadata_name,
                "embeddings": embeddings_name,
                "embeddingsJson": embeddings_json_name,
                "encoding": "base64",
                "count": end - start,
                "metadataBytes": len(metadata_bytes),
                "embeddingBytes": len(vector_bytes),
                "embeddingsJsonBytes": len(embeddings_json_bytes),
                "metadataSha256": sha256_bytes(metadata_bytes),
                "embeddingSha256": vector_sha256,
                "embeddingsJsonSha256": sha256_bytes(embeddings_json_bytes),
            }
        )

    source_pages = len({chunk.sourcePath for chunk in chunks})
    sections = Counter(chunk.sectionKey for chunk in chunks)
    manifest = {
        "version": 2,
        "ready": True,
        "generatedAt": datetime.now(UTC).isoformat(),
        "model": MODEL_ID,
        "modelRevision": MODEL_REVISION,
        "browserModel": BROWSER_MODEL_ID,
        "browserModelRevision": BROWSER_MODEL_REVISION,
        "corpusBaseUrl": BASE_URL,
        "dimensions": DIMENSIONS,
        "dtype": "float16",
        "normalized": True,
        "queryPrefix": "query: ",
        "passagePrefix": "passage: ",
        "documentCount": source_pages,
        "chunkCount": len(chunks),
        "sections": dict(sorted(sections.items())),
        "shards": shards,
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--output", type=Path, default=Path("ai-search/data"), help="Output directory")
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    parser.add_argument("--overlap-chars", type=int, default=DEFAULT_OVERLAP_CHARS)
    parser.add_argument("--shard-size", type=int, default=DEFAULT_SHARD_SIZE)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args(argv)

    if args.chunk_chars < 300:
        parser.error("--chunk-chars must be at least 300")
    if not 0 <= args.overlap_chars < args.chunk_chars:
        parser.error("--overlap-chars must be between 0 and chunk size")
    if args.shard_size < 100:
        parser.error("--shard-size must be at least 100")
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = build_index(args)
    except Exception as exc:
        print(f"semantic-index build failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Generated {manifest['chunkCount']:,} chunks from "
        f"{manifest['documentCount']:,} HTML pages in {len(manifest['shards'])} shards",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
