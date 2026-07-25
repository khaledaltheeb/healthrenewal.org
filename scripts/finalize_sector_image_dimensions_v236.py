from __future__ import annotations

import json
import re
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

VERSION = 236
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
ATTR_TEMPLATE = r"\b{name}\s*=\s*([\"'])(.*?)\1"
ILLUSTRATION_TOKEN = "/assets/illustrations/"


def attribute(tag: str, name: str) -> str | None:
    match = re.search(ATTR_TEMPLATE.format(name=re.escape(name)), tag, re.IGNORECASE | re.DOTALL)
    return match.group(2).strip() if match else None


def positive_dimension(value: str | None) -> str | None:
    if not value:
        return None
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(?:px)?\s*", value, re.IGNORECASE)
    if not match:
        return None
    try:
        number = Decimal(match.group(1))
    except InvalidOperation:
        return None
    if number <= 0:
        return None
    rounded = int(number.to_integral_value(rounding=ROUND_HALF_UP))
    return str(max(1, rounded))


def svg_dimensions(path: Path) -> tuple[str, str] | None:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None

    width = positive_dimension(root.attrib.get("width"))
    height = positive_dimension(root.attrib.get("height"))
    if width and height:
        return width, height

    view_box = root.attrib.get("viewBox") or root.attrib.get("viewbox")
    if not view_box:
        return None
    values = re.split(r"[\s,]+", view_box.strip())
    if len(values) != 4:
        return None
    width = positive_dimension(values[2])
    height = positive_dimension(values[3])
    if not width or not height:
        return None
    return width, height


def illustration_name(src: str | None) -> str | None:
    if not src:
        return None
    path = urlsplit(src).path.replace("\\", "/")
    if ILLUSTRATION_TOKEN not in path:
        return None
    name = Path(path).name
    return name if name.lower().endswith(".svg") else None


def append_dimensions(tag: str, width: str, height: str) -> tuple[str, int]:
    additions: list[str] = []
    if attribute(tag, "width") is None:
        additions.append(f'width="{width}"')
    if attribute(tag, "height") is None:
        additions.append(f'height="{height}"')
    if not additions:
        return tag, 0

    stripped = tag.rstrip()
    if stripped.endswith("/>"):
        body = stripped[:-2].rstrip()
        return body + " " + " ".join(additions) + " />", len(additions)
    body = stripped[:-1].rstrip()
    return body + " " + " ".join(additions) + ">", len(additions)


def find_missing(text: str, dimensions: dict[str, tuple[str, str]]) -> list[str]:
    missing: list[str] = []
    for tag in IMG_RE.findall(text):
        name = illustration_name(attribute(tag, "src"))
        if not name:
            continue
        if name not in dimensions:
            missing.append(f"{name}:intrinsic-dimensions-unavailable")
            continue
        if attribute(tag, "width") is None or attribute(tag, "height") is None:
            missing.append(f"{name}:html-dimensions-missing")
    return missing


def finalize(site: Path = SITE) -> dict[str, object]:
    site = Path(site).resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")

    illustrations = site / "assets" / "illustrations"
    sectors = site / "sectors"
    dimension_map: dict[str, tuple[str, str]] = {}
    invalid_svgs: list[str] = []
    if illustrations.is_dir():
        for svg in sorted(illustrations.glob("*.svg")):
            dimensions = svg_dimensions(svg)
            if dimensions:
                dimension_map[svg.name] = dimensions
            else:
                invalid_svgs.append(svg.name)

    pages_scanned = 0
    target_images = 0
    images_updated = 0
    attributes_added = 0
    changed_pages: list[str] = []
    unresolved: list[dict[str, object]] = []

    if sectors.is_dir():
        for page in sorted(sectors.rglob("*.html")):
            pages_scanned += 1
            original = page.read_text(encoding="utf-8")

            def replace(match: re.Match[str]) -> str:
                nonlocal target_images, images_updated, attributes_added
                tag = match.group(0)
                name = illustration_name(attribute(tag, "src"))
                if not name:
                    return tag
                target_images += 1
                dimensions = dimension_map.get(name)
                if not dimensions:
                    return tag
                updated, additions = append_dimensions(tag, *dimensions)
                if additions:
                    images_updated += 1
                    attributes_added += additions
                return updated

            updated = IMG_RE.sub(replace, original)
            if updated != original:
                page.write_text(updated, encoding="utf-8")
                changed_pages.append(page.relative_to(site).as_posix())

            remaining = find_missing(updated, dimension_map)
            if remaining:
                unresolved.append(
                    {
                        "page": page.relative_to(site).as_posix(),
                        "issues": remaining,
                    }
                )

    report: dict[str, object] = {
        "version": VERSION,
        "status": "passed" if not unresolved else "failed",
        "scope": "sector-svg-illustrations",
        "illustrations_scanned": len(dimension_map) + len(invalid_svgs),
        "illustrations_with_dimensions": len(dimension_map),
        "invalid_svg_dimensions": invalid_svgs,
        "pages_scanned": pages_scanned,
        "target_images": target_images,
        "images_updated": images_updated,
        "attributes_added": attributes_added,
        "changed_pages": changed_pages,
        "remaining_missing_dimensions": len(unresolved),
        "unresolved": unresolved,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "sector-image-dimensions-v236.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if unresolved:
        raise SystemExit(f"Sector illustration dimensions remain unresolved: {unresolved[:10]}")
    return report


def main() -> None:
    print(json.dumps(finalize(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
