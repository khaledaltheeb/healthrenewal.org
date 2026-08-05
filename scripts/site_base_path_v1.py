from __future__ import annotations

from urllib.parse import urlsplit


def normalize_site_base_path(base_url: str) -> str:
    """Return one absolute path prefix for a site URL.

    Root-domain deployments resolve to ``/`` and subpath deployments resolve
    to ``/subpath/``. The function never returns a protocol-relative ``//``
    prefix, which browsers interpret as a different host.
    """
    value = str(base_url or "").strip()
    if not value:
        return "/"

    parsed = urlsplit(value)
    path = parsed.path if parsed.scheme or parsed.netloc else value
    segments = [segment for segment in path.split("/") if segment and segment != "."]
    if not segments:
        return "/"
    return "/" + "/".join(segments) + "/"
