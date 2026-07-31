#!/usr/bin/env python3
"""Audit specialist interfaces with intentional dual-Worker recovery fallback."""

from __future__ import annotations

import audit_specialists_partners_v354_base as _base
from audit_specialists_partners_v354_base import *  # noqa: F401,F403

PAGES = dict(_base.PAGES)
PAGES["recover"] = (
    "specialists-partners/recover/index.html",
    False,
    {CORE_ORIGIN, IDENTITY_ORIGIN, TURNSTILE_ORIGIN},
)
PAGES["password_reset"] = (
    "specialists-partners/password-reset/index.html",
    False,
    {CORE_ORIGIN, IDENTITY_ORIGIN},
)
_base.PAGES = PAGES

audit = _base.audit
parse_args = _base.parse_args
main = _base.main


if __name__ == "__main__":
    raise SystemExit(main())
