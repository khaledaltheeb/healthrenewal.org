from __future__ import annotations

"""مدخل متوافق لمولّد الصفحة الرئيسية مع تطبيق الهيدر المؤسسي v233."""

try:
    from scripts import apply_homepage_v20_base as _base
    from scripts.publish_institutional_header_v233 import publish as _publish_header
except ModuleNotFoundError:
    import apply_homepage_v20_base as _base
    from publish_institutional_header_v233 import publish as _publish_header


for _name in dir(_base):
    if not _name.startswith("_") and _name != "main":
        globals()[_name] = getattr(_base, _name)


def main() -> None:
    _base.main()
    report = _publish_header(_base.SITE)
    if report.get("status") != "passed":
        raise SystemExit(f"Institutional header v233 failed: {report}")


if __name__ == "__main__":
    main()
