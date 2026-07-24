from __future__ import annotations

import csv
import html
import io
import ipaddress
import json
import re
import socket
import sys
import unicodedata
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "content" / "integrations" / "course-sources-v215.json"
DEFAULT_OUTPUT = ROOT / ".build" / "authorized-courses-v215.json"
SCHEMA_VERSION = 215
SECURITY_CONTRACT_VERSION = 218
MAX_RESPONSE_BYTES = 5_000_000
MAX_COURSES_PER_SOURCE = 5_000
TEXT_LIMITS = {
    "id": 160,
    "title": 220,
    "title_ar": 220,
    "description": 2_000,
    "description_ar": 2_000,
    "provider": 220,
    "language": 32,
    "format": 80,
    "duration": 120,
    "price_text": 120,
}
HTML_TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
HOST_LABEL_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)"
    r"(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*$"
)
COURSE_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,158}[A-Za-z0-9])?$")


class CourseImportError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovedSource:
    source_id: str
    provider: str
    feed_url: str
    feed_format: str
    allowed_hosts: tuple[str, ...]
    course_hosts: tuple[str, ...]
    permission_reference: str
    permission_granted_at: str
    permission_duration: str
    permission_expires_at: str | None
    license_url: str


def clean_text(value: Any, limit: int) -> str:
    text = html.unescape(str(value or ""))
    text = HTML_TAG_RE.sub(" ", text)
    text = "".join(
        character
        for character in text
        if (character >= " " or character in "\n\t")
        and unicodedata.category(character) not in {"Cf", "Cs"}
    )
    text = SPACE_RE.sub(" ", text).strip()
    return text[:limit]


def parse_https_url(value: Any, field: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(str(value or "").strip())
    if parsed.scheme != "https" or not parsed.netloc or not parsed.hostname:
        raise CourseImportError(f"{field} must be an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise CourseImportError(f"{field} must not contain credentials")
    if parsed.fragment:
        raise CourseImportError(f"{field} must not contain a fragment")
    try:
        port = parsed.port
    except ValueError as exc:
        raise CourseImportError(f"{field} contains an invalid port") from exc
    if port not in {None, 443}:
        raise CourseImportError(f"{field} must use the default HTTPS port")
    return parsed


def validate_date(value: Any, field: str, *, allow_future: bool = False) -> str:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise CourseImportError(f"{field} must use YYYY-MM-DD") from exc
    if not allow_future and parsed > date.today():
        raise CourseImportError(f"{field} cannot be in the future")
    return text


def normalize_host(value: Any, field: str) -> str:
    raw = clean_text(value, 253).strip().rstrip(".").lower()
    if not raw or any(token in raw for token in ("/", "\\", "@", "*", ":")):
        raise CourseImportError(f"{field} must contain a plain DNS hostname")
    try:
        host = raw.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise CourseImportError(f"{field} contains an invalid hostname") from exc
    if host == "localhost" or host.endswith(
        (".localhost", ".local", ".internal", ".home", ".lan")
    ):
        raise CourseImportError(f"{field} must not use a local hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise CourseImportError(f"{field} must not use an IP literal")
    if len(host) > 253 or not HOST_LABEL_RE.fullmatch(host):
        raise CourseImportError(f"{field} contains an invalid DNS hostname")
    return host


def validate_permission_window(
    raw: dict[str, Any], source_id: str
) -> tuple[str, str | None]:
    duration = clean_text(raw.get("permission_duration"), 20).lower()
    expires_raw = raw.get("permission_expires_at")
    if duration == "perpetual":
        if expires_raw not in {None, ""}:
            raise CourseImportError(
                f"source {source_id}: perpetual permission must use a null permission_expires_at"
            )
        return duration, None
    if duration != "fixed":
        raise CourseImportError(
            f"source {source_id}: permission_duration must be fixed or perpetual"
        )
    expires_at = validate_date(
        expires_raw, "permission_expires_at", allow_future=True
    )
    if date.fromisoformat(expires_at) < date.today():
        raise CourseImportError(f"source {source_id}: permission has expired")
    return duration, expires_at


def validate_source(raw: dict[str, Any]) -> ApprovedSource:
    source_id = clean_text(raw.get("id"), 120)
    provider = clean_text(raw.get("provider"), 220)
    if not source_id or not re.fullmatch(
        r"[a-z0-9][a-z0-9-]{1,118}[a-z0-9]", source_id
    ):
        raise CourseImportError("source id must be a stable lowercase slug")
    if not provider:
        raise CourseImportError(f"source {source_id}: provider is required")
    if raw.get("permission_status") != "approved":
        raise CourseImportError(
            f"source {source_id}: permission_status must be approved"
        )
    if "import_catalog" not in set(raw.get("allowed_actions") or []):
        raise CourseImportError(
            f"source {source_id}: import_catalog permission is required"
        )

    permission_reference = clean_text(raw.get("permission_reference"), 500)
    if not permission_reference:
        raise CourseImportError(
            f"source {source_id}: permission_reference is required"
        )
    permission_granted_at = validate_date(
        raw.get("permission_granted_at"), "permission_granted_at"
    )
    permission_duration, permission_expires_at = validate_permission_window(
        raw, source_id
    )
    license_url = parse_https_url(raw.get("license_url"), "license_url").geturl()

    feed_format = clean_text(raw.get("format"), 20).lower()
    if feed_format not in {"json", "csv"}:
        raise CourseImportError(
            f"source {source_id}: format must be json or csv"
        )
    feed = parse_https_url(raw.get("feed_url"), "feed_url")

    allowed_hosts = tuple(
        sorted(
            {
                normalize_host(host, "allowed_hosts")
                for host in raw.get("allowed_hosts") or []
            }
        )
    )
    if not allowed_hosts:
        raise CourseImportError(f"source {source_id}: allowed_hosts is required")
    feed_host = normalize_host(feed.hostname, "feed host")
    if feed_host not in allowed_hosts:
        raise CourseImportError(
            f"source {source_id}: feed host is not allowlisted"
        )

    course_hosts = tuple(
        sorted(
            {
                normalize_host(host, "course_hosts")
                for host in (raw.get("course_hosts") or allowed_hosts)
            }
        )
    )
    return ApprovedSource(
        source_id=source_id,
        provider=provider,
        feed_url=feed.geturl(),
        feed_format=feed_format,
        allowed_hosts=allowed_hosts,
        course_hosts=course_hosts,
        permission_reference=permission_reference,
        permission_granted_at=permission_granted_at,
        permission_duration=permission_duration,
        permission_expires_at=permission_expires_at,
        license_url=license_url,
    )


def public_addresses_from_answers(host: str, answers: Iterable[Any]) -> tuple[str, ...]:
    addresses: set[str] = set()
    for answer in answers:
        try:
            value = str(answer[4][0]).split("%", 1)[0]
        except (IndexError, TypeError) as exc:
            raise CourseImportError(
                f"host {host} returned an invalid DNS answer"
            ) from exc
        try:
            address = ipaddress.ip_address(value)
        except ValueError as exc:
            raise CourseImportError(
                f"host {host} resolved to an invalid address"
            ) from exc
        if not address.is_global:
            raise CourseImportError(
                f"host {host} resolved to a non-public address"
            )
        addresses.add(address.compressed)
    if not addresses:
        raise CourseImportError(
            f"host {host} did not resolve to a public address"
        )
    return tuple(sorted(addresses))


def ensure_public_dns(host: str) -> tuple[str, ...]:
    try:
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise CourseImportError(f"host resolution failed for {host}") from exc
    return public_addresses_from_answers(host, answers)


class PinnedDnsResolver:
    def __init__(self) -> None:
        self._original = socket.getaddrinfo
        self._pins: dict[str, tuple[str, ...]] = {}

    def pin(self, host: str) -> tuple[str, ...]:
        normalized = normalize_host(host, "network host")
        if normalized not in self._pins:
            try:
                answers = self._original(
                    normalized, 443, type=socket.SOCK_STREAM
                )
            except OSError as exc:
                raise CourseImportError(
                    f"host resolution failed for {normalized}"
                ) from exc
            self._pins[normalized] = public_addresses_from_answers(
                normalized, answers
            )
        return self._pins[normalized]

    def getaddrinfo(
        self,
        host: str,
        port: int | str | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> list[tuple[int, int, int, str, tuple[Any, ...]]]:
        del flags
        normalized = normalize_host(host, "connection host")
        if normalized not in self._pins:
            raise socket.gaierror(
                socket.EAI_NONAME,
                f"unvalidated DNS target blocked: {normalized}",
            )
        results: list[tuple[int, int, int, str, tuple[Any, ...]]] = []
        selected_type = type or socket.SOCK_STREAM
        selected_proto = proto or socket.IPPROTO_TCP
        for value in self._pins[normalized]:
            address = ipaddress.ip_address(value)
            address_family = (
                socket.AF_INET6 if address.version == 6 else socket.AF_INET
            )
            if family not in {0, socket.AF_UNSPEC, address_family}:
                continue
            sockaddr: tuple[Any, ...]
            if address.version == 6:
                sockaddr = (address.compressed, port, 0, 0)
            else:
                sockaddr = (address.compressed, port)
            results.append(
                (
                    address_family,
                    selected_type,
                    selected_proto,
                    "",
                    sockaddr,
                )
            )
        if not results:
            raise socket.gaierror(
                socket.EAI_FAMILY,
                f"no pinned DNS address matches requested family for {normalized}",
            )
        return results

    @contextmanager
    def active(self) -> Iterator[None]:
        current = socket.getaddrinfo
        socket.getaddrinfo = self.getaddrinfo
        try:
            yield
        finally:
            socket.getaddrinfo = current


def validate_network_target(
    url: str,
    source: ApprovedSource,
    field: str,
    resolver: PinnedDnsResolver | None = None,
) -> urllib.parse.ParseResult:
    parsed = parse_https_url(url, field)
    host = normalize_host(parsed.hostname, f"{field} host")
    if host not in source.allowed_hosts:
        raise CourseImportError(
            f"source {source.source_id}: {field} escaped the host allowlist"
        )
    if resolver is None:
        ensure_public_dns(host)
    else:
        resolver.pin(host)
    return parsed


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(
        self,
        source: ApprovedSource,
        resolver: PinnedDnsResolver | None = None,
    ) -> None:
        super().__init__()
        self.source = source
        self.resolver = resolver or PinnedDnsResolver()

    def redirect_request(
        self, req, fp, code, msg, headers, newurl
    ):  # type: ignore[no-untyped-def]
        validate_network_target(
            newurl,
            self.source,
            "redirect URL",
            self.resolver,
        )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_response_limited(response: Any) -> bytes:
    declared = response.headers.get("Content-Length")
    if declared:
        try:
            declared_size = int(declared)
        except ValueError as exc:
            raise CourseImportError(
                "course feed returned an invalid Content-Length"
            ) from exc
        if declared_size < 0:
            raise CourseImportError(
                "course feed returned a negative Content-Length"
            )
        if declared_size > MAX_RESPONSE_BYTES:
            raise CourseImportError(
                "course feed exceeds the maximum allowed size"
            )
    payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CourseImportError(
            "course feed exceeds the maximum allowed size"
        )
    return payload


def fetch_feed(source: ApprovedSource) -> bytes:
    resolver = PinnedDnsResolver()
    validate_network_target(
        source.feed_url, source, "feed URL", resolver
    )
    request = urllib.request.Request(
        source.feed_url,
        headers={
            "Accept": "application/json,text/csv;q=0.9,text/plain;q=0.5",
            "User-Agent": (
                f"PterminologyAuthorizedCourseImporter/"
                f"{SECURITY_CONTRACT_VERSION}"
            ),
        },
        method="GET",
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        SafeRedirectHandler(source, resolver),
    )
    with resolver.active():
        with opener.open(request, timeout=20) as response:
            validate_network_target(
                response.geturl(), source, "final URL", resolver
            )
            return read_response_limited(response)


def parse_feed(payload: bytes, feed_format: str) -> list[dict[str, Any]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CourseImportError("course feed must use UTF-8") from exc
    if feed_format == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CourseImportError(
                "course feed contains invalid JSON"
            ) from exc
        rows = data.get("courses") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise CourseImportError(
                "JSON feed must be a list or an object with a courses list"
            )
        if any(not isinstance(row, dict) for row in rows):
            raise CourseImportError(
                "each JSON course record must be an object"
            )
        return rows
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CourseImportError("CSV feed must include a header row")
    return [dict(row) for row in reader]


def normalize_course(
    raw: dict[str, Any], source: ApprovedSource
) -> dict[str, Any]:
    course_id = clean_text(
        raw.get("id") or raw.get("course_id") or raw.get("slug"),
        TEXT_LIMITS["id"],
    )
    title_ar = clean_text(
        raw.get("title_ar") or raw.get("arabic_title"),
        TEXT_LIMITS["title_ar"],
    )
    title = clean_text(
        raw.get("title") or raw.get("name"), TEXT_LIMITS["title"]
    )
    if not course_id:
        course_id = re.sub(
            r"[^a-z0-9]+", "-", title.lower()
        ).strip("-")[:120]
    if not course_id or not (title_ar or title):
        raise CourseImportError(
            f"source {source.source_id}: each course needs an id and title"
        )
    if not COURSE_ID_RE.fullmatch(course_id):
        raise CourseImportError(
            f"source {source.source_id}: course id must use letters, digits, dot, underscore, or hyphen"
        )

    course_url = parse_https_url(
        raw.get("url") or raw.get("course_url"), "course url"
    )
    course_host = normalize_host(
        course_url.hostname, "course URL host"
    )
    if course_host not in source.course_hosts:
        raise CourseImportError(
            f"source {source.source_id}: course URL host is not allowlisted"
        )

    updated_at = clean_text(
        raw.get("updated_at") or raw.get("date_modified"), 40
    )
    if updated_at:
        try:
            parsed_updated = datetime.fromisoformat(
                updated_at.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise CourseImportError(
                f"source {source.source_id}: invalid course updated_at"
            ) from exc
        if (
            parsed_updated.tzinfo is None
            or parsed_updated.utcoffset() is None
        ):
            raise CourseImportError(
                f"source {source.source_id}: course updated_at must include a timezone"
            )

    return {
        "id": f"{source.source_id}:{course_id}",
        "source_id": source.source_id,
        "provider": source.provider,
        "title_ar": title_ar,
        "title": title,
        "description_ar": clean_text(
            raw.get("description_ar") or raw.get("arabic_description"),
            TEXT_LIMITS["description_ar"],
        ),
        "description": clean_text(
            raw.get("description"), TEXT_LIMITS["description"]
        ),
        "url": course_url.geturl(),
        "language": clean_text(
            raw.get("language") or "", TEXT_LIMITS["language"]
        ),
        "format": clean_text(
            raw.get("format") or raw.get("delivery_mode") or "",
            TEXT_LIMITS["format"],
        ),
        "duration": clean_text(
            raw.get("duration") or "", TEXT_LIMITS["duration"]
        ),
        "price_text": clean_text(
            raw.get("price_text") or raw.get("price") or "",
            TEXT_LIMITS["price_text"],
        ),
        "updated_at": updated_at or None,
        "license_url": source.license_url,
        "permission_status": "approved",
        "permission_expires_at": source.permission_expires_at,
    }


def deduplicate(
    courses: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    seen_urls: dict[str, str] = {}
    for course in courses:
        course_id = course["id"]
        url = course["url"]
        if course_id in by_id:
            raise CourseImportError(f"duplicate course id: {course_id}")
        if url in seen_urls:
            raise CourseImportError(f"duplicate course URL: {url}")
        by_id[course_id] = course
        seen_urls[url] = course_id
    return [by_id[key] for key in sorted(by_id)]


def import_courses(
    manifest_path: Path = DEFAULT_MANIFEST,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CourseImportError(
            "invalid course source manifest JSON"
        ) from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("policy") != "deny-by-default"
    ):
        raise CourseImportError("invalid course source manifest contract")
    raw_sources = manifest.get("sources")
    if not isinstance(raw_sources, list):
        raise CourseImportError("sources must be a list")

    approved: list[ApprovedSource] = []
    source_ids: set[str] = set()
    for raw in raw_sources:
        if not isinstance(raw, dict):
            raise CourseImportError("each source must be an object")
        if not raw.get("enabled", False):
            continue
        source = validate_source(raw)
        if source.source_id in source_ids:
            raise CourseImportError(
                f"duplicate enabled source id: {source.source_id}"
            )
        source_ids.add(source.source_id)
        approved.append(source)

    normalized: list[dict[str, Any]] = []
    for source in approved:
        rows = parse_feed(fetch_feed(source), source.feed_format)
        if len(rows) > MAX_COURSES_PER_SOURCE:
            raise CourseImportError(
                f"source {source.source_id}: too many courses"
            )
        normalized.extend(
            normalize_course(row, source) for row in rows
        )

    courses = deduplicate(normalized)
    result = {
        "schema_version": SCHEMA_VERSION,
        "security_contract_version": SECURITY_CONTRACT_VERSION,
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "status": "ready" if approved else "no-approved-sources",
        "sources_processed": len(approved),
        "courses": courses,
        "security": {
            "permission_window_required": True,
            "https_port": 443,
            "redirects_checked_before_request": True,
            "dns_public_addresses_only": True,
            "dns_answers_pinned_during_connection": True,
            "proxies_disabled": True,
            "maximum_response_bytes": MAX_RESPONSE_BYTES,
            "maximum_courses_per_source": MAX_COURSES_PER_SOURCE,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(output_path)
    return result


def main() -> int:
    arguments = [Path(value).resolve() for value in sys.argv[1:]]
    manifest = next(
        (value for value in arguments if value.suffix.lower() == ".json"),
        DEFAULT_MANIFEST,
    )
    output = next(
        (
            value
            for value in arguments
            if value.suffix.lower() == ".json" and value != manifest
        ),
        DEFAULT_OUTPUT,
    )
    result = import_courses(manifest, output)
    print(
        json.dumps(
            {
                "status": result["status"],
                "sources_processed": result["sources_processed"],
                "courses": len(result["courses"]),
                "security_contract_version": SECURITY_CONTRACT_VERSION,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
