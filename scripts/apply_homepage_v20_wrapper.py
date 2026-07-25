from __future__ import annotations

"""غلاف إنتاجي يحافظ على مولّد الصفحة الحالي ثم يطبّق الهيدر المؤسسي."""

from pathlib import Path

from scripts.publish_institutional_header_v233 import publish


def finalize_header(site: Path | str) -> dict[str, object]:
    """طبّق الهيدر على حزمة سبق أن أنشأها مولّد الصفحة الرئيسية."""
    return publish(site)
