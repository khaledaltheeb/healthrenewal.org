#!/usr/bin/env python3
"""Run the established Discover enhancer for the 250-page edition."""

import enhance_quick_info_discover as enhancer


def main() -> None:
    enhancer.EXPECTED_COUNT = 250
    enhancer.PUBLISHED_ISO = "2026-08-04T10:05:00+03:00"
    enhancer.PUBLISHED_RFC822 = "Tue, 04 Aug 2026 10:05:00 +0300"
    enhancer.main()


if __name__ == "__main__":
    main()
