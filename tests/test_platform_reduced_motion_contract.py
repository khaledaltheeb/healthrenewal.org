from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "assets/platform/platform-core.css"
JS_PATH = ROOT / "assets/platform/platform-core.js"


class ReducedMotionContract:
    """Small source validator used by both production checks and negative fixtures."""

    MEDIA_QUERY = re.compile(
        r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{(?P<body>.*?)\n\}",
        re.DOTALL,
    )

    @classmethod
    def validate_css(cls, css: str) -> list[str]:
        errors: list[str] = []
        match = cls.MEDIA_QUERY.search(css)
        if not match:
            return ["platform CSS is missing a prefers-reduced-motion: reduce block"]

        block = match.group("body")
        normalized = re.sub(r"\s+", " ", block)
        if "scroll-behavior: auto" not in normalized:
            errors.append("reduced-motion CSS must disable smooth scrolling")
        if "animation-duration: 0.01ms !important" not in normalized:
            errors.append("reduced-motion CSS must collapse animation duration")
        if "animation-iteration-count: 1 !important" not in normalized:
            errors.append("reduced-motion CSS must prevent repeated animation")
        if "transition-duration: 0.01ms !important" not in normalized:
            errors.append("reduced-motion CSS must collapse transition duration")
        return errors

    @staticmethod
    def validate_js(js: str) -> list[str]:
        errors: list[str] = []
        if not re.search(
            r"matchMedia\(\s*['\"]\(prefers-reduced-motion:\s*reduce\)['\"]\s*\)",
            js,
        ):
            errors.append("platform JavaScript must read the reduced-motion preference")

        scroll_call = re.search(
            r"scrollTo\s*\(\s*\{(?P<body>.*?)\}\s*\)",
            js,
            re.DOTALL,
        )
        if not scroll_call:
            errors.append("platform JavaScript is missing the back-to-top scroll contract")
        else:
            body = re.sub(r"\s+", " ", scroll_call.group("body"))
            if not re.search(
                r"behavior\s*:\s*reducedMotion\.matches\s*\?\s*['\"]auto['\"]\s*:\s*['\"]smooth['\"]",
                body,
            ):
                errors.append(
                    "back-to-top scrolling must use auto when reduced motion is requested"
                )
        return errors


class PlatformReducedMotionContractTests(unittest.TestCase):
    def test_production_platform_sources_satisfy_contract(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")
        js = JS_PATH.read_text(encoding="utf-8")

        errors = ReducedMotionContract.validate_css(css)
        errors.extend(ReducedMotionContract.validate_js(js))
        self.assertEqual([], errors, "\n".join(errors))

    def test_css_contract_rejects_missing_media_query(self) -> None:
        errors = ReducedMotionContract.validate_css("html { scroll-behavior: smooth; }")
        self.assertTrue(errors)
        self.assertIn("missing", errors[0])

    def test_css_contract_rejects_smooth_scrolling_inside_reduced_mode(self) -> None:
        css = """
        @media (prefers-reduced-motion: reduce) {
          html { scroll-behavior: smooth; }
          * { animation-duration: 0.01ms !important;
              animation-iteration-count: 1 !important;
              transition-duration: 0.01ms !important; }
        }
        """
        errors = ReducedMotionContract.validate_css(css)
        self.assertIn("reduced-motion CSS must disable smooth scrolling", errors)

    def test_css_contract_rejects_repeating_animation(self) -> None:
        css = """
        @media (prefers-reduced-motion: reduce) {
          html { scroll-behavior: auto; }
          * { animation-duration: 0.01ms !important;
              animation-iteration-count: infinite !important;
              transition-duration: 0.01ms !important; }
        }
        """
        errors = ReducedMotionContract.validate_css(css)
        self.assertIn("reduced-motion CSS must prevent repeated animation", errors)

    def test_js_contract_rejects_unconditional_smooth_scroll(self) -> None:
        js = """
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        """
        errors = ReducedMotionContract.validate_js(js)
        self.assertIn(
            "back-to-top scrolling must use auto when reduced motion is requested",
            errors,
        )

    def test_js_contract_accepts_preference_aware_scroll(self) -> None:
        js = """
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        window.scrollTo({
          top: 0,
          behavior: reducedMotion.matches ? 'auto' : 'smooth'
        });
        """
        self.assertEqual([], ReducedMotionContract.validate_js(js))


if __name__ == "__main__":
    unittest.main()
