from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/apply_tools_descendant_marshmallow_v250.py"


def dark_page(title: str, *, single_quotes: bool = False) -> str:
    body = "<body class='existing-tool-page'>" if single_quotes else '<body class="existing-tool-page">'
    return (
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        f"<title>{title}</title>"
        "<style>"
        "body{background:#071f27;color:#08272d}"
        ".quiz-panel,.question,.option,.result{background:#102f38;color:#0a3338}"
        ".option{border:1px solid #163f45}"
        "</style></head>"
        f"{body}<main><section class=\"quiz-panel\"><h1>{title}</h1>"
        '<article class="question"><h2>السؤال</h2><p class="question-text">اختر الإجابة.</p>'
        '<label class="option" for="answer-a"><input id="answer-a" type="radio" name="a">الإجابة الأولى</label>'
        '<div class="result"><strong>النتيجة</strong><p>شرح النتيجة.</p></div>'
        "</article></section></main></body></html>"
    )


def relative_luminance(color: str) -> float:
    raw = color.removeprefix("#")
    channels = [int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4)]

    def linearize(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


class ToolsDescendantMarshmallowV250Tests(unittest.TestCase):
    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="tools-descendant-v250-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        for relative, title, single_quotes in (
            ("tools/index.html", "الأدوات", False),
            ("tools/quiz/index.html", "اختبار المصطلحات", True),
            ("tools/glossary/index.html", "المصطلحات", False),
            ("tools/deep/example/index.html", "أداة فرعية", False),
        ):
            path = site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(dark_page(title, single_quotes=single_quotes), encoding="utf-8")
        outside = site / "outside/index.html"
        outside.parent.mkdir(parents=True)
        outside.write_text(dark_page("خارج الأدوات"), encoding="utf-8")
        return site

    def run_publisher(self, site: Path) -> None:
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)

    def test_applies_light_marshmallow_contrast_to_root_and_every_child(self) -> None:
        site = self.make_site()
        outside_before = (site / "outside/index.html").read_bytes()

        self.run_publisher(site)

        tool_pages = sorted((site / "tools").rglob("*.html"))
        self.assertEqual(len(tool_pages), 4)
        for page in tool_pages:
            text = page.read_text(encoding="utf-8")
            self.assertIn('data-tools-design="marshmallow-v245"', text)
            self.assertIn("tools-marshmallow-v245", text)
            self.assertIn("tools-descendant-marshmallow-v250", text)
            self.assertEqual(text.count('id="tools-marshmallow-v245-style"'), 1)
            self.assertEqual(text.count('id="tools-descendant-marshmallow-v250-style"'), 1)
            self.assertIn("--tm-mint:#e5faf5", text)
            self.assertIn("--tdm-mint:#e5faf5", text)
            self.assertIn(
                "background:linear-gradient(145deg,#fff,var(--tdm-mint))!important",
                text,
            )
            self.assertIn("color:var(--tdm-ink)!important", text)
            self.assertIn("@media(prefers-color-scheme:dark)", text)

        quiz = (site / "tools/quiz/index.html").read_text(encoding="utf-8")
        self.assertIn("class='existing-tool-page tools-marshmallow-v245 tools-descendant-marshmallow-v250'", quiz)
        self.assertIn(".quiz-panel", quiz)
        self.assertIn(".question", quiz)
        self.assertIn(".option", quiz)
        self.assertIn(".result", quiz)

        self.assertEqual((site / "outside/index.html").read_bytes(), outside_before)
        report = json.loads(
            (site / "api/tools-descendant-marshmallow-v250.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["status"], "published")
        self.assertEqual(report["pages"], 4)
        self.assertEqual(report["child_pages"], 3)
        self.assertTrue(report["quiz_fixed"])
        self.assertEqual(report["unstyled_pages"], [])
        self.assertIn("tools/quiz/index.html", report["routes"])

    def test_palette_exceeds_wcag_aa_for_normal_text(self) -> None:
        foregrounds = {
            "primary": "#173f45",
            "muted": "#4d686b",
            "heading": "#5b2946",
            "button": "#103f42",
        }
        backgrounds = {
            "white": "#ffffff",
            "mint": "#e5faf5",
            "rose": "#fff0f5",
            "lilac": "#f2edff",
            "peach": "#fff0e8",
        }
        ratios = {
            f"{foreground_name}_on_{background_name}": contrast_ratio(foreground, background)
            for foreground_name, foreground in foregrounds.items()
            for background_name, background in backgrounds.items()
        }
        failures = {name: ratio for name, ratio in ratios.items() if ratio < 4.5}
        self.assertEqual(failures, {}, ratios)
        self.assertGreaterEqual(min(ratios.values()), 5.2)

    def test_second_run_is_byte_stable(self) -> None:
        site = self.make_site()
        self.run_publisher(site)
        first = {
            page.relative_to(site).as_posix(): page.read_bytes()
            for page in sorted((site / "tools").rglob("*.html"))
        }

        self.run_publisher(site)
        second = {
            page.relative_to(site).as_posix(): page.read_bytes()
            for page in sorted((site / "tools").rglob("*.html"))
        }
        self.assertEqual(first, second)
        report = json.loads(
            (site / "api/tools-descendant-marshmallow-v250.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["updated"], 0)
        self.assertEqual(report["unchanged"], 4)

    def test_missing_quiz_page_is_rejected(self) -> None:
        site = self.make_site()
        (site / "tools/quiz/index.html").unlink()
        completed = subprocess.run(
            ["python3", str(SCRIPT), str(site)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("tools/quiz/index.html: missing page", completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
