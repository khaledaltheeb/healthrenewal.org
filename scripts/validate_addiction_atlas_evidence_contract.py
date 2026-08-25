from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/addiction-atlas"
MANIFEST = DATA / "substance-waves.json"
PROJECT_TODAY = datetime.now(ZoneInfo("Asia/Amman")).date()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise AssertionError(message)


def parse_wave(route: str) -> str:
    prefix = "/data/addiction-atlas/substances-"
    suffix = ".json"
    if not route.startswith(prefix) or not route.endswith(suffix):
        fail(f"invalid registered wave route: {route!r}")
    wave = route[len(prefix):-len(suffix)]
    if not wave or not wave.startswith("v"):
        fail(f"invalid wave identifier: {wave!r}")
    return wave


def load_sources() -> tuple[dict[str, dict], list[str]]:
    paths = sorted(DATA.glob("source-registry-v*.json"))
    if not paths:
        fail("no source-registry shards found")
    source_by_id: dict[str, dict] = {}
    shard_names: set[str] = set()
    for path in paths:
        payload = load(path)
        shard = payload.get("registry_shard") or path.stem
        if shard in shard_names:
            fail(f"duplicate registry shard name: {shard}")
        shard_names.add(shard)
        sources = payload.get("sources") or []
        if not sources:
            fail(f"empty source registry shard: {path.name}")
        for source in sources:
            source_id = source.get("id")
            if not source_id:
                fail(f"{path.name}: source missing id")
            if source_id in source_by_id:
                fail(f"duplicate source id across registry shards: {source_id}")
            parsed = urlparse(source.get("url", ""))
            if parsed.scheme != "https" or not parsed.netloc:
                fail(f"{path.name}:{source_id}: invalid HTTPS source URL")
            verified_on = source.get("verified_on")
            try:
                verified = date.fromisoformat(verified_on)
            except (TypeError, ValueError):
                fail(f"{path.name}:{source_id}: invalid verified_on={verified_on!r}")
            if verified > PROJECT_TODAY:
                fail(f"{path.name}:{source_id}: future verified_on relative to Asia/Amman")
            source_by_id[source_id] = source
    return source_by_id, [p.name for p in paths]


def main() -> None:
    manifest = load(MANIFEST)
    routes = manifest.get("waves") or []
    if not routes:
        fail("empty substance wave manifest")

    wave_files: dict[str, Path] = {}
    wave_slugs: dict[str, set[str]] = {}
    all_slugs: set[str] = set()
    for route in routes:
        wave = parse_wave(route)
        if wave in wave_files:
            fail(f"duplicate wave in manifest: {wave}")
        path = ROOT / route.lstrip("/")
        if not path.is_file():
            fail(f"registered wave file missing: {route}")
        payload = load(path)
        slugs = {item.get("slug") for item in payload.get("substances", [])}
        if None in slugs or "" in slugs:
            fail(f"{path.name}: substance missing slug")
        if len(slugs) != len(payload.get("substances", [])):
            fail(f"{path.name}: duplicate substance slug within wave")
        overlap = all_slugs & slugs
        if overlap:
            fail(f"substance slugs duplicated across waves: {sorted(overlap)}")
        all_slugs |= slugs
        wave_files[wave] = path
        wave_slugs[wave] = slugs

    source_by_id, registry_files = load_sources()

    map_paths = sorted(DATA.glob("source-map-v*.json"))
    if not map_paths:
        fail("no source-map shards found")
    map_by_wave: dict[str, Path] = {}
    mapped_slugs: set[str] = set()
    record_count = 0
    used_source_ids: set[str] = set()

    for path in map_paths:
        payload = load(path)
        wave = payload.get("wave")
        if not wave:
            fail(f"{path.name}: missing wave")
        if wave in map_by_wave:
            fail(f"multiple source maps registered for {wave}: {map_by_wave[wave].name}, {path.name}")
        map_by_wave[wave] = path
        if wave not in wave_slugs:
            fail(f"{path.name}: maps unregistered wave {wave}")

        records = payload.get("records") or []
        record_slugs = [record.get("substance_slug") for record in records]
        if any(not slug for slug in record_slugs):
            fail(f"{path.name}: record missing substance_slug")
        if len(record_slugs) != len(set(record_slugs)):
            fail(f"{path.name}: duplicate substance source-map record")
        record_set = set(record_slugs)
        if record_set != wave_slugs[wave]:
            fail(
                f"{path.name}: coverage mismatch for {wave}; "
                f"missing={sorted(wave_slugs[wave] - record_set)} "
                f"extra={sorted(record_set - wave_slugs[wave])}"
            )

        overlap = mapped_slugs & record_set
        if overlap:
            fail(f"substances mapped by multiple source-map shards: {sorted(overlap)}")
        mapped_slugs |= record_set
        record_count += len(records)

        for record in records:
            ids = record.get("source_ids") or []
            if not ids:
                fail(f"{path.name}:{record['substance_slug']}: source_ids required")
            if len(ids) != len(set(ids)):
                fail(f"{path.name}:{record['substance_slug']}: duplicate source_ids")
            unknown = set(ids) - set(source_by_id)
            if unknown:
                fail(f"{path.name}:{record['substance_slug']}: unknown source_ids {sorted(unknown)}")
            used_source_ids |= set(ids)
            supports = record.get("supports") or []
            if not supports:
                fail(f"{path.name}:{record['substance_slug']}: supports required")

    registered_waves = set(wave_slugs)
    mapped_waves = set(map_by_wave)
    if mapped_waves != registered_waves:
        fail(
            "source-map/manifest wave contract mismatch; "
            f"missing_maps={sorted(registered_waves - mapped_waves)} "
            f"orphan_maps={sorted(mapped_waves - registered_waves)}"
        )

    if mapped_slugs != all_slugs:
        fail(
            "global evidence coverage incomplete; "
            f"missing={sorted(all_slugs - mapped_slugs)} extra={sorted(mapped_slugs - all_slugs)}"
        )
    if record_count != len(all_slugs):
        fail(f"source-map record count must equal substance count: {record_count} != {len(all_slugs)}")

    unused_sources = sorted(set(source_by_id) - used_source_ids)

    print(
        json.dumps(
            {
                "status": "passed",
                "registeredWaves": len(registered_waves),
                "sourceMapShards": len(map_by_wave),
                "substances": len(all_slugs),
                "mappedSubstances": len(mapped_slugs),
                "sourceMapRecords": record_count,
                "sourceRegistryShards": len(registry_files),
                "sourceRegistryEntries": len(source_by_id),
                "usedSourceEntries": len(used_source_ids),
                "unusedSourceEntries": len(unused_sources),
                "unusedSourceIds": unused_sources,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
