#!/usr/bin/env python3
"""Validate the repository's public accessibility governance baseline.

This validator checks that the public statement and its machine-readable
evaluation record stay aligned and do not make unsupported certification or
conformance claims.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

STATEMENT_PATH = Path("accessibility/index.html")
EVALUATION_PATH = Path("accessibility/evaluation.json")
README_PATH = Path("README.md")
CANONICAL_URL = "https://healthrenewal.org/accessibility/"
FEEDBACK_URL = "https://github.com/khaledaltheeb/healthrenewal.org/issues/new/choose"
ALLOWED_STATUSES = {"baseline-in-progress", "partial", "conformant"}
ALLOWED_LIMITATION_STATUSES = {"open", "monitoring", "resolved"}

POSITIVE_CERTIFICATION_PATTERNS = (
    re.compile(r"\bW3C[\s-]+(?:certified|approved|accredited)\b", re.IGNORECASE),
    re.compile(r"(?:المنصة|الموقع|نحن).{0,40}(?:معتمد|موثق|حاصل على شهادة).{0,25}W3C", re.IGNORECASE | re.DOTALL),
)
POSITIVE_CONFORMANCE_PATTERNS = (
    re.compile(r"(?:نمتثل|متوافق(?:ة)? بالكامل|امتثال كامل).{0,35}WCAG\s*2\.2", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bfully conform(?:ant|s).{0,25}WCAG\s*2\.2\b", re.IGNORECASE | re.DOTALL),
)


@dataclass
class StatementParser(HTMLParser):
    html_lang: str | None = None
    html_dir: str | None = None
    titles: list[str] = field(default_factory=list)
    meta_description: str | None = None
    canonical: str | None = None
    json_alternate: str | None = None
    main_ids: list[str] = field(default_factory=list)
    skip_links: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    _capture_title: bool = False
    _capture_heading: bool = False
    _buffer: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs}
        tag = tag.lower()

        if tag == "html":
            self.html_lang = values.get("lang")
            self.html_dir = values.get("dir")
        elif tag == "title":
            self._capture_title = True
            self._buffer = []
        elif tag in {"h1", "h2"}:
            self._capture_heading = True
            self._buffer = []
        elif tag == "meta" and (values.get("name") or "").lower() == "description":
            self.meta_description = values.get("content")
        elif tag == "link":
            rel = set((values.get("rel") or "").lower().split())
            if "canonical" in rel:
                self.canonical = values.get("href")
            if "alternate" in rel and (values.get("type") or "").lower() == "application/json":
                self.json_alternate = values.get("href")
        elif tag == "main":
            self.main_ids.append(values.get("id") or "")
        elif tag == "a":
            href = values.get("href") or ""
            self.links.append(href)
            classes = set((values.get("class") or "").split())
            if "skip" in classes:
                self.skip_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title" and self._capture_title:
            self.titles.append("".join(self._buffer).strip())
            self._capture_title = False
            self._buffer = []
        elif tag in {"h1", "h2"} and self._capture_heading:
            self.headings.append("".join(self._buffer).strip())
            self._capture_heading = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_title or self._capture_heading:
            self._buffer.append(data)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{path} must contain a JSON object")
        return {}
    return data


def parse_iso_date(value: Any, field_name: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{field_name} must be an ISO date string")
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{field_name} must use YYYY-MM-DD")
        return None


def contains_positive_claim(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def validate_statement(root: Path, errors: list[str]) -> str:
    path = root / STATEMENT_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing file: {STATEMENT_PATH}")
        return ""

    parser = StatementParser()
    try:
        parser.feed(text)
    except Exception as exc:
        errors.append(f"unable to parse {STATEMENT_PATH}: {exc}")
        return text

    if parser.html_lang != "ar":
        errors.append("accessibility statement must declare html lang='ar'")
    if parser.html_dir != "rtl":
        errors.append("accessibility statement must declare html dir='rtl'")
    if len(parser.titles) != 1 or not parser.titles[0]:
        errors.append("accessibility statement must contain exactly one non-empty title")
    if not parser.meta_description or len(parser.meta_description.strip()) < 50:
        errors.append("accessibility statement needs a useful meta description")
    if parser.canonical != CANONICAL_URL:
        errors.append(f"canonical URL must be {CANONICAL_URL}")
    if parser.json_alternate != "evaluation.json":
        errors.append("statement must link to evaluation.json as application/json")
    if parser.main_ids != ["main"]:
        errors.append("statement must contain exactly one <main id='main'>")
    if "#main" not in parser.skip_links:
        errors.append("statement must provide a skip link to #main")
    if not any(heading for heading in parser.headings):
        errors.append("statement must contain visible headings")
    if FEEDBACK_URL not in parser.links:
        errors.append("statement must expose the governed accessibility feedback route")

    required_fragments = (
        "WCAG 2.2",
        "المستوى AA",
        "WCAG-EM 2.0",
        "لا يوجد في هذه المرحلة ادعاء امتثال كامل",
        "لا تمثل اعتمادًا صادرًا عن W3C",
        "بيانات صحية أو تعريفية",
    )
    for fragment in required_fragments:
        if fragment not in text:
            errors.append(f"statement missing required transparency text: {fragment}")

    if contains_positive_claim(text, POSITIVE_CERTIFICATION_PATTERNS):
        errors.append("statement contains an unsupported positive W3C certification claim")
    if contains_positive_claim(text, POSITIVE_CONFORMANCE_PATTERNS):
        errors.append("statement contains an unsupported full WCAG conformance claim")

    return text


def validate_evaluation(root: Path, errors: list[str]) -> dict[str, Any]:
    data = load_json(root / EVALUATION_PATH, errors)
    if not data:
        return data

    if data.get("schemaVersion") != "1.0":
        errors.append("evaluation schemaVersion must be '1.0'")
    if data.get("page") != "/accessibility/":
        errors.append("evaluation page must be /accessibility/")
    if data.get("language") != "ar":
        errors.append("evaluation language must be ar")
    if data.get("status") not in ALLOWED_STATUSES:
        errors.append(f"evaluation status must be one of {sorted(ALLOWED_STATUSES)}")

    target = data.get("target")
    if not isinstance(target, dict):
        errors.append("evaluation target must be an object")
    else:
        if target.get("standard") != "WCAG 2.2":
            errors.append("target.standard must be WCAG 2.2")
        if target.get("level") != "AA":
            errors.append("target.level must be AA")
        if target.get("methodology") != "WCAG-EM 2.0":
            errors.append("target.methodology must be WCAG-EM 2.0")

    claim = data.get("conformanceClaim")
    if not isinstance(claim, dict):
        errors.append("conformanceClaim must be an object")
    else:
        if claim.get("status") != "none":
            errors.append("conformanceClaim.status must remain 'none' until a verified scoped evaluation exists")
        if claim.get("date") is not None:
            errors.append("conformanceClaim.date must be null while status is none")
        if claim.get("scope") is not None:
            errors.append("conformanceClaim.scope must be null while status is none")
        if claim.get("independentReview") is not False:
            errors.append("conformanceClaim.independentReview must be false until independent review is evidenced")

    claims = data.get("claims")
    if not isinstance(claims, dict):
        errors.append("claims must be an object")
    else:
        if claims.get("w3cCertified") is not False:
            errors.append("claims.w3cCertified must be false")
        if claims.get("thirdPartyCertified") is not False:
            errors.append("claims.thirdPartyCertified must be false until evidence is recorded")

    today = datetime.now(ZoneInfo("Asia/Amman")).date()
    last_review = parse_iso_date(data.get("lastInternalReview"), "lastInternalReview", errors)
    next_review = parse_iso_date(data.get("nextReviewDue"), "nextReviewDue", errors)
    if last_review and last_review > today:
        errors.append("lastInternalReview cannot be in the future in Asia/Amman")
    if last_review and next_review and next_review < last_review:
        errors.append("nextReviewDue cannot be earlier than lastInternalReview")

    scope = data.get("evaluationScope")
    if not isinstance(scope, dict):
        errors.append("evaluationScope must be an object")
    else:
        routes = scope.get("representativeRoutes")
        if not isinstance(routes, list) or len(routes) < 6:
            errors.append("evaluationScope.representativeRoutes must contain at least six routes")
        elif len(routes) != len(set(routes)):
            errors.append("representativeRoutes must be unique")
        elif any(not isinstance(route, str) or not route.startswith("/") for route in routes):
            errors.append("every representative route must be an absolute site path")

        browsers = scope.get("browsersPlanned")
        if not isinstance(browsers, list) or len(set(browsers)) < 4:
            errors.append("browsersPlanned must identify at least four unique browsers")

        assistive = scope.get("assistiveTechnologyPlanned")
        if not isinstance(assistive, list) or len(set(assistive)) < 5:
            errors.append("assistiveTechnologyPlanned must identify at least five unique technologies or modes")

    limitations = data.get("knownLimitations")
    if not isinstance(limitations, list) or len(limitations) < 3:
        errors.append("knownLimitations must contain at least three transparent limitations")
    else:
        ids: list[str] = []
        for index, item in enumerate(limitations):
            if not isinstance(item, dict):
                errors.append(f"knownLimitations[{index}] must be an object")
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not re.fullmatch(r"[a-z0-9-]+", item_id):
                errors.append(f"knownLimitations[{index}].id must be a lowercase slug")
            else:
                ids.append(item_id)
            if item.get("status") not in ALLOWED_LIMITATION_STATUSES:
                errors.append(f"knownLimitations[{index}].status is invalid")
            summary = item.get("summary")
            if not isinstance(summary, str) or len(summary.strip()) < 30:
                errors.append(f"knownLimitations[{index}].summary is too short")
        if len(ids) != len(set(ids)):
            errors.append("known limitation IDs must be unique")

    feedback = data.get("feedback")
    if not isinstance(feedback, dict):
        errors.append("feedback must be an object")
    else:
        if feedback.get("channel") != "github-issues":
            errors.append("feedback.channel must be github-issues")
        if feedback.get("public") is not True:
            errors.append("feedback.public must explicitly be true")
        if feedback.get("url") != FEEDBACK_URL:
            errors.append("feedback.url must use the repository issue chooser")
        warning = feedback.get("privacyWarning")
        if not isinstance(warning, str) or "بيانات صحية" not in warning or "رموز دخول" not in warning:
            errors.append("feedback.privacyWarning must prohibit sensitive health and access data")

    serialized = json.dumps(data, ensure_ascii=False)
    if contains_positive_claim(serialized, POSITIVE_CERTIFICATION_PATTERNS):
        errors.append("evaluation data contains an unsupported positive W3C certification claim")
    if contains_positive_claim(serialized, POSITIVE_CONFORMANCE_PATTERNS):
        errors.append("evaluation data contains an unsupported full WCAG conformance claim")

    return data


def validate_readme(root: Path, errors: list[str]) -> None:
    path = root / README_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append("missing README.md")
        return
    if CANONICAL_URL not in text:
        errors.append("README.md must link to the public accessibility statement")
    if contains_positive_claim(text, POSITIVE_CERTIFICATION_PATTERNS):
        errors.append("README.md contains an unsupported positive W3C certification claim")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    validate_statement(root, errors)
    validate_evaluation(root, errors)
    validate_readme(root, errors)
    return errors


def write_fixture(root: Path) -> None:
    (root / "accessibility").mkdir(parents=True, exist_ok=True)
    (root / "accessibility/index.html").write_text(
        """<!doctype html><html lang="ar" dir="rtl"><head>
<title>إفادة الإتاحة</title>
<meta name="description" content="وصف عربي واضح وطويل بما يكفي للتحقق من إفادة الإتاحة المنشورة وحالتها الحالية.">
<link rel="canonical" href="https://healthrenewal.org/accessibility/">
<link rel="alternate" type="application/json" href="evaluation.json">
</head><body><a class="skip" href="#main">تجاوز</a><main id="main">
<h1>إفادة الإتاحة</h1><p>WCAG 2.2 بالمستوى AA وWCAG-EM 2.0.</p>
<p>لا يوجد في هذه المرحلة ادعاء امتثال كامل.</p>
<p>هذه الصفحة لا تمثل اعتمادًا صادرًا عن W3C.</p>
<p>لا تنشر بيانات صحية أو تعريفية.</p>
<a href="https://github.com/khaledaltheeb/healthrenewal.org/issues/new/choose">بلاغ</a>
</main></body></html>""",
        encoding="utf-8",
    )
    fixture = {
        "schemaVersion": "1.0",
        "page": "/accessibility/",
        "language": "ar",
        "status": "baseline-in-progress",
        "target": {"standard": "WCAG 2.2", "level": "AA", "methodology": "WCAG-EM 2.0"},
        "conformanceClaim": {"status": "none", "date": None, "scope": None, "independentReview": False},
        "lastInternalReview": "2026-01-01",
        "nextReviewDue": "2026-12-31",
        "evaluationScope": {
            "representativeRoutes": ["/", "/a/", "/b/", "/c/", "/d/", "/e/"],
            "browsersPlanned": ["Chrome", "Firefox", "Edge", "Safari"],
            "assistiveTechnologyPlanned": ["NVDA", "VoiceOver", "TalkBack", "keyboard-only", "voice-input"],
        },
        "knownLimitations": [
            {"id": "one", "status": "open", "summary": "هذا وصف طويل بما يكفي للقيد الأول في الاختبار الذاتي."},
            {"id": "two", "status": "monitoring", "summary": "هذا وصف طويل بما يكفي للقيد الثاني في الاختبار الذاتي."},
            {"id": "three", "status": "resolved", "summary": "هذا وصف طويل بما يكفي للقيد الثالث في الاختبار الذاتي."},
        ],
        "feedback": {
            "channel": "github-issues",
            "public": True,
            "url": FEEDBACK_URL,
            "privacyWarning": "لا تنشر رموز دخول أو بيانات صحية أو تعريفية.",
        },
        "claims": {"w3cCertified": False, "thirdPartyCertified": False},
    }
    (root / "accessibility/evaluation.json").write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(CANONICAL_URL + "\n", encoding="utf-8")


def run_self_test() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture(root)
        errors = validate(root)
        if errors:
            print("self-test valid fixture failed:", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1

        evaluation_path = root / EVALUATION_PATH
        data = json.loads(evaluation_path.read_text(encoding="utf-8"))
        data["claims"]["w3cCertified"] = True
        evaluation_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        errors = validate(root)
        if not any("w3cCertified" in error for error in errors):
            print("self-test failed to reject unsupported W3C certification", file=sys.stderr)
            return 1

        write_fixture(root)
        statement_path = root / STATEMENT_PATH
        statement_path.write_text(
            statement_path.read_text(encoding="utf-8").replace(
                "</main>", "<p>W3C certified</p></main>"
            ),
            encoding="utf-8",
        )
        errors = validate(root)
        if not any("positive W3C certification" in error for error in errors):
            print("self-test failed to reject positive certification wording", file=sys.stderr)
            return 1

    print("accessibility governance validator self-test: passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    errors = validate(args.root.resolve())
    if errors:
        print("accessibility governance validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("accessibility governance validation: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
