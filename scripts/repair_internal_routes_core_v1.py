from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

BASE = "https://healthrenewal.org"
REPORT = "api/internal-route-repair-v1.json"
INTERNAL_HOSTS = {"healthrenewal.org", "www.healthrenewal.org"}

HUBS = {
    "/special-needs/practical/": (
        "أدوات وتطبيقات عملية لذوي الاحتياجات الخاصة",
        "مركز تطبيقي يجمع الأدلة العملية الجاهزة للاستخدام في المنزل والمدرسة والخدمات، مع إبقاء التقييم الفردي والسلامة في المقدمة.",
    ),
    "/special-needs/early-intervention/": (
        "التدخل المبكر: أدلة عملية للأسرة والفريق",
        "مركز يجمع أدلة التدخل المبكر حول التواصل والحركة والاستعداد للمدرسة والتدريب الأسري والانتقالات، مع التركيز على المشاركة والوظيفة اليومية.",
    ),
    "/special-needs/learning/": (
        "صعوبات التعلم والقراءة والكتابة والرياضيات",
        "مركز عربي يجمع أدلة صعوبات التعلم والقراءة والكتابة والرياضيات والتقييم والدعم المدرسي والأسري بصورة مترابطة.",
    ),
    "/special-needs/education/": (
        "التربية الخاصة والتعليم الدامج",
        "مركز يجمع أدلة التربية الخاصة والتعليم الدامج والخطط الفردية وغرف المصادر والخدمات المساندة والتكييفات والدعم السلوكي.",
    ),
}

PATHS = {
    "/learning-paths/institutional-resources/": {
        "title": "مسار استخدام المصادر المؤسسية الموثوقة",
        "desc": "مسار عملي للوصول إلى المصادر المؤسسية وفهم نوع الدليل وحدوده ثم توثيق المصدر ومراجعته قبل استخدامه.",
        "steps": [
            ("ابدأ بدليل المصادر الموثقة", "/verified-resources/", "تعرف إلى الجهات والموارد التي راجعتها روافد."),
            ("تحقق من سجل المصدر", "/source-registry/", "راجع هوية المصدر ونطاقه وحالته."),
            ("راجع منهج الثقة", "/trust/", "افهم الفصل بين الدليل والتفسير وحدود الاستخدام والتحديث."),
        ],
    },
    "/learning-paths/special-education/": {
        "title": "مسار أساسيات التربية الخاصة والتعليم الدامج",
        "desc": "مسار تطبيقي لفهم التعليم الدامج والخطة الفردية وغرفة المصادر والخدمات المساندة والتكييفات وقياس التقدم.",
        "steps": [
            ("ابدأ بمركز التربية الخاصة", "/special-needs/education/", "كوّن صورة عامة عن الأدلة التعليمية المتاحة."),
            ("افهم الخطة الفردية", "/family-guide/tools/individualized-education-plan/", "حوّل الاحتياجات إلى أهداف قابلة للقياس وأدوار واضحة."),
            ("راجع دور غرفة المصادر", "/special-needs/education/resource-room/", "ميّز بين الدعم الموجه للمهارة وبين مجرد فصل الطالب عن الصف."),
            ("نسّق الخدمات المساندة", "/special-needs/education/related-services/", "اربط الخدمة بهدف وظيفي وتعليمي واضح."),
            ("فرّق بين التيسير والتعديل", "/family-guide/tools/accommodations-modifications/", "اختر ما يزيل حاجز الوصول وما يغيّر متطلبات المهمة بوضوح."),
        ],
    },
    "/learning-paths/writing-spelling-intervention-arabic/": {
        "title": "مسار تدخلات الكتابة والإملاء بالعربية",
        "desc": "مسار عربي يربط تقييم صعوبات الكتابة بالتدخل المنظم والتيسيرات المنزلية والمدرسية ومراقبة التقدم.",
        "steps": [
            ("افهم نمط صعوبة الكتابة", "/special-needs/learning/dysgraphia/", "ميّز بين الخط والتهجئة والتعبير والمكونات الحركية واللغوية."),
            ("انقل الدعم إلى المنزل", "/family-guide/learning-support/writing-difficulties-at-home/", "اختر هدفًا صغيرًا قابلًا للملاحظة."),
            ("أزل حواجز الوصول", "/family-guide/tools/accommodations-modifications/", "استخدم التيسيرات عندما يكون الهدف إتاحة التعبير."),
            ("راقب التقدم", "/family-guide/tools/progress-monitoring/", "قارن عينات متكررة بالمؤشر نفسه قبل تغيير الخطة."),
        ],
    },
    "/learning-paths/intensive-arabic-reading-intervention/": {
        "title": "مسار التدخل المكثف في القراءة العربية",
        "desc": "مسار عربي متدرج من الوعي الصوتي وفك الترميز إلى الطلاقة والفهم مع ربط التقييم بنوع التدخل ومراقبة الاستجابة.",
        "steps": [
            ("ابدأ بالوعي الصوتي", "/special-needs/learning/arabic-phonological-awareness-reading-difficulties/", "حدّد الصعوبة في تحليل الأصوات والدمج والتجزئة وعلاقتها بالخط والتشكيل."),
            ("افهم عسر القراءة", "/special-needs/learning/dyslexia/", "اربط العلامات بالتقييم التعليمي ولا تستخدم تشخيصًا ذاتيًا من عرض منفرد."),
            ("ابن الطلاقة بعد الدقة", "/special-needs/learning/arabic-reading-fluency-learning-difficulties/", "درّب القراءة المتصلة دون التضحية بالدقة أو المعنى."),
            ("افصل الفهم عن فك الكلمات", "/special-needs/learning/arabic-reading-comprehension-learning-difficulties/", "راجع اللغة والمفردات والاستدلال وبنية النص عندما تكون الدقة جيدة والفهم ضعيفًا."),
            ("انقل الخطة إلى المنزل", "/family-guide/learning-support/reading-difficulties-at-home/", "اجعل التدريب قصيرًا ومتكررًا ومتسقًا مع هدف المدرسة."),
        ],
    },
    "/learning-paths/evidence-guided/inclusive-education-foundations/": {
        "title": "مسار أسس التعليم الدامج المبني على الدليل",
        "desc": "مسار يربط مبادئ التعليم الدامج والتصميم الشامل للتعلم بالتكييفات والتقييم القابل للوصول ومراجعة أثر الدعم في الصف.",
        "steps": [
            ("افهم الوصول والمشاركة", "/special-needs/science/inclusive-education-access/", "ابدأ من العوائق الوظيفية في البيئة لا من تسمية التشخيص وحدها."),
            ("استخدم مبادئ UDL", "/special-needs/reference/udlinclusive-education-guide/", "نوّع طرق الوصول والمشاركة والتعبير قبل اللجوء إلى حلول فردية معزولة."),
            ("خطط لتكييف الصف", "/special-needs/inclusive-classroom-adjustments-plan/", "اربط كل تكييف بحاجز محدد ومؤشر نجاح وموعد مراجعة."),
            ("اجعل التقييم قابلًا للوصول", "/special-needs/accessible-classroom-assessment-design/", "افصل ما تريد قياسه عن العوائق غير المقصودة في طريقة عرض الاختبار أو الاستجابة."),
            ("حوّل المبادئ إلى درس", "/special-needs/udl-lesson-planning-rubric/", "راجع تصميم الدرس نفسه بدل انتظار فشل الطالب ثم إضافة تعديلات متأخرة."),
        ],
    },
    "/learning-paths/positive-behavior-support/": {
        "title": "مسار الدعم السلوكي الإيجابي",
        "desc": "مسار عملي لفهم وظيفة السلوك وجمع الملاحظات وتعليم بدائل قابلة للاستخدام وقياس أثر الدعم دون وصم الطفل.",
        "steps": [
            ("ابدأ بالسياق والوظيفة", "/special-needs/education/classroom-behavior-support/", "صف ما يحدث قبل السلوك وبعده وما الذي قد يحافظ عليه."),
            ("اجمع ملاحظات منظمة", "/family-guide/tools/behavior-log/", "استخدم سجلًا مختصرًا للأنماط المتكررة دون تحويل الملاحظة إلى تشخيص."),
            ("ابن خطة دعم وظيفية", "/family-guide/tools/functional-behavior-support-plan/", "حدد مهارة بديلة وتعديلًا بيئيًا واستجابة متسقة."),
            ("راجع دليل الدعم الإيجابي", "/special-needs/guides/sensory-behavior/positive-behavior-support/", "وازن بين الوقاية والتعليم والاستجابة."),
        ],
    },
    "/learning-paths/accessible-content-creator/": {
        "title": "مسار إنشاء محتوى رقمي قابل للوصول",
        "desc": "مسار عملي لبناء محتوى يمكن قراءته والتنقل فيه وفهمه واستخدامه عبر الهاتف ولوحة المفاتيح والتقنيات المساندة.",
        "steps": [
            ("ابدأ بإمكانية الوصول", "/accessibility/", "راجع مبادئ الوصول في المنصة."),
            ("راجع اللغة الواضحة", "/trust/", "اكتب حدود الاستخدام والمصدر بلغة مباشرة."),
        ],
    },
}

ALIASES = {
    "/family-guide/tools/iep/": "/family-guide/tools/individualized-education-plan/",
    "/autism/": "/special-needs/autism/",
}

LINK_REPLACEMENTS = {
    "/family-guide/tools/iep/": "/family-guide/tools/individualized-education-plan/",
    "/autism/": "/special-needs/autism/",
    "/special-needs/learning/arabic-reading-fluency-learning-difficulties/": "/special-needs/learning/arabic-reading-fluency/",
}

REQUIRED_EXISTING_ROUTES = {
    "/learning-paths/intensive-mathematics-intervention-special-education/": "صفحة المسار الرياضي الأصلية الغنية",
}


def _target(root: Path, route: str) -> Path:
    relative = route.strip("/")
    return root / relative / "index.html" if relative else root / "index.html"


def _exists(root: Path, href: str) -> bool:
    parsed = urlsplit(href)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return True
    if parsed.netloc and parsed.netloc.lower() not in INTERNAL_HOSTS:
        return True
    path = unquote(parsed.path or "/")
    if path == "/":
        return (root / "index.html").is_file()
    candidate = root / path.lstrip("/")
    if path.endswith("/"):
        return (candidate / "index.html").is_file()
    return candidate.is_file() or (candidate / "index.html").is_file()


def _page(title: str, desc: str, route: str, links: list[tuple[str, str, str]]) -> str:
    items = "".join(
        f'<article class="card"><h2>{html.escape(label)}</h2><p>{html.escape(note)}</p><p><a href="{html.escape(href)}">افتح الدليل</a></p></article>'
        for label, href, note in links
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} | روافد</title><meta name="description" content="{html.escape(desc)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}{route}"><style>body{{margin:0;background:#f6faf9;color:#173f43;font-family:Tahoma,Arial,sans-serif;line-height:2}}main{{width:min(1100px,92%);margin:auto;padding:32px 0}}.hero,.card{{background:#fff;border:1px solid #cfe4df;border-radius:18px;padding:22px;margin:16px 0}}h1{{line-height:1.4}}a{{color:#075c49}}</style></head><body><main><section class="hero"><h1>{html.escape(title)}</h1><p>{html.escape(desc)}</p></section>{items}</main></body></html>'''


def _alias_page(route: str, target_route: str) -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>تم نقل الصفحة | روافد</title><meta name="robots" content="noindex,follow"><link rel="canonical" href="{BASE}{html.escape(target_route)}"><meta http-equiv="refresh" content="0;url={html.escape(target_route)}"></head><body><main><h1>تم نقل هذه الصفحة</h1><p>انتقل المحتوى إلى عنوانه المعتمد.</p><p><a href="{html.escape(target_route)}">فتح الصفحة المعتمدة</a></p></main></body></html>'''


def _hub_links(root: Path, route: str) -> list[tuple[str, str, str]]:
    base = root / route.strip("/")
    if not base.is_dir():
        return []
    links: list[tuple[str, str, str]] = []
    for child in sorted(base.iterdir()):
        page = child / "index.html"
        if not child.is_dir() or not page.is_file():
            continue
        href = "/" + child.relative_to(root).as_posix().strip("/") + "/"
        title = child.name.replace("-", " ")
        try:
            source = page.read_text(encoding="utf-8")
            match = re.search(r"<h1[^>]*>(.*?)</h1>", source, re.I | re.S)
            if match:
                title = re.sub(r"<[^>]+>", " ", match.group(1)).strip() or title
        except (OSError, UnicodeError):
            pass
        links.append((title, href, "دليل مرتبط ضمن هذا المركز."))
    return links[:60]


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.base_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.lower() == "base" and self.base_href is None and values.get("href"):
            self.base_href = str(values["href"]).strip()
        elif tag.lower() == "a" and values.get("href"):
            self.hrefs.append(str(values["href"]).strip())


def _page_url(root: Path, page: Path) -> str:
    rel = page.relative_to(root).as_posix()
    if rel == "index.html":
        return BASE + "/"
    if rel.endswith("/index.html"):
        return BASE + "/" + rel[:-10]
    return BASE + "/" + rel


def _audit_internal_links(root: Path) -> dict:
    missing: list[dict[str, str]] = []
    html_files = 0
    internal_links = 0
    for page in root.rglob("*.html"):
        html_files += 1
        try:
            source = page.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        parser = _AnchorParser()
        try:
            parser.feed(source)
        except Exception:
            continue
        page_url = _page_url(root, page)
        base_url = urljoin(page_url, parser.base_href) if parser.base_href else page_url
        for href in parser.hrefs:
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            resolved = urlsplit(urljoin(base_url, href))
            if resolved.scheme not in {"http", "https"} or resolved.netloc.lower() not in INTERNAL_HOSTS:
                continue
            internal_links += 1
            target_path = unquote(resolved.path or "/")
            if not _exists(root, target_path):
                missing.append({
                    "source": page.relative_to(root).as_posix(),
                    "href": href,
                    "target": target_path,
                })
    distinct = sorted({item["target"] for item in missing})
    return {
        "htmlFilesScanned": html_files,
        "internalLinksChecked": internal_links,
        "missingCount": len(missing),
        "distinctMissingTargets": distinct,
        "missingOccurrences": missing,
    }


def _rewrite_known_internal_links(root: Path) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for page in root.rglob("*.html"):
        try:
            source = page.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        updated = source
        for old, new in LINK_REPLACEMENTS.items():
            patterns = (
                (f'href="{old}"', f'href="{new}"'),
                (f"href='{old}'", f"href='{new}'"),
                (f'href="{BASE}{old}"', f'href="{BASE}{new}"'),
                (f"href='{BASE}{old}'", f"href='{BASE}{new}'"),
            )
            for before, after in patterns:
                count = updated.count(before)
                if count:
                    updated = updated.replace(before, after)
                    changes.append({
                        "source": page.relative_to(root).as_posix(),
                        "from": old,
                        "to": new,
                        "count": str(count),
                    })
        if updated != source:
            page.write_text(updated, encoding="utf-8")
    return changes


_CARD_RE = re.compile(
    r"<article\b[^>]*class=[\"'][^\"']*\bcomplete-discovery-card\b[^\"']*[\"'][^>]*>.*?</article>",
    re.I | re.S,
)
_CARD_HREF_RE = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"']", re.I | re.S)


def _prune_missing_discovery_cards(root: Path) -> list[dict[str, str]]:
    removed: list[dict[str, str]] = []
    for page in root.rglob("all-pages/index.html"):
        try:
            source = page.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        def repl(match: re.Match[str]) -> str:
            block = match.group(0)
            href_match = _CARD_HREF_RE.search(block)
            if not href_match:
                return block
            href = html.unescape(href_match.group(1)).strip()
            parsed = urlsplit(href)
            if parsed.scheme and parsed.scheme not in {"http", "https"}:
                return block
            if parsed.netloc and parsed.netloc.lower() not in INTERNAL_HOSTS:
                return block
            if _exists(root, href):
                return block
            removed.append({
                "source": page.relative_to(root).as_posix(),
                "target": unquote(parsed.path or href),
            })
            return ""

        updated = _CARD_RE.sub(repl, source)
        if updated == source:
            continue
        card_count = len(_CARD_RE.findall(updated))
        updated = re.sub(r'("numberOfItems"\s*:\s*)\d+', rf'\g<1>{card_count}', updated, count=1)
        updated = re.sub(r'(العدد:\s*)\d+(\s*\.)', rf'\g<1>{card_count}\g<2>', updated, count=1)
        page.write_text(updated, encoding="utf-8")
    return removed


def apply(root: Path) -> dict:
    root = Path(root).resolve()
    generated: list[str] = []
    hub_status: dict[str, str] = {}
    path_status: dict[str, str] = {}
    alias_status: dict[str, str] = {}
    missing_step_targets: list[dict[str, str]] = []
    required_missing: list[dict[str, str]] = []

    for route, (title, desc) in HUBS.items():
        target = _target(root, route)
        if target.is_file():
            hub_status[route] = "existing"
            continue
        links = _hub_links(root, route)
        if not links:
            hub_status[route] = "missing-children"
            required_missing.append({"route": route, "reason": "hub-has-no-published-children"})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_page(title, desc, route, links), encoding="utf-8")
        generated.append(route)
        hub_status[route] = "generated"

    for route, spec in PATHS.items():
        target = _target(root, route)
        if target.is_file():
            path_status[route] = "existing"
            continue
        valid_steps: list[tuple[str, str, str]] = []
        for label, href, note in spec["steps"]:
            if _exists(root, href):
                valid_steps.append((label, href, note))
            else:
                missing_step_targets.append({"route": route, "href": href})
        if len(valid_steps) < 2:
            path_status[route] = "insufficient-valid-steps"
            required_missing.append({"route": route, "reason": "learning-path-has-fewer-than-two-valid-steps"})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_page(spec["title"], spec["desc"], route, valid_steps), encoding="utf-8")
        generated.append(route)
        path_status[route] = "generated"

    for route, target_route in ALIASES.items():
        alias_target = _target(root, route)
        if alias_target.is_file():
            alias_status[route] = "existing"
            continue
        if not _exists(root, target_route):
            alias_status[route] = "canonical-target-missing"
            required_missing.append({"route": route, "reason": "alias-canonical-target-missing", "target": target_route})
            continue
        alias_target.parent.mkdir(parents=True, exist_ok=True)
        alias_target.write_text(_alias_page(route, target_route), encoding="utf-8")
        generated.append(route)
        alias_status[route] = f"generated->{target_route}"

    rewritten_links = _rewrite_known_internal_links(root)
    pruned_discovery_cards = _prune_missing_discovery_cards(root)

    for route, label in REQUIRED_EXISTING_ROUTES.items():
        if not _exists(root, route):
            required_missing.append({"route": route, "reason": "required-source-authored-route-missing", "label": label})

    audit = _audit_internal_links(root)
    passed = not required_missing and audit["missingCount"] == 0
    report = {
        "status": "passed" if passed else "failed",
        "generatedRoutes": generated,
        "hubs": hub_status,
        "learningPaths": path_status,
        "aliases": alias_status,
        "rewrittenLinks": rewritten_links,
        "prunedDiscoveryCards": pruned_discovery_cards,
        "audit": {
            **audit,
            "missingStepTargets": missing_step_targets,
            "requiredMissing": required_missing,
        },
    }
    report_path = root / REPORT
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
