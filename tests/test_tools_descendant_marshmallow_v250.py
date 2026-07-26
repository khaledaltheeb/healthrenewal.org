from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/apply_tools_descendant_marshmallow_v250.py"


def load_publisher() -> object:
    spec = importlib.util.spec_from_file_location("tools_descendant_marshmallow_v252", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dark_page(
    title: str,
    *,
    single_quotes: bool = False,
    stale_contract: bool = False,
    duplicate_descendant_style: bool = False,
) -> str:
    body = "<body class='existing-tool-page'>" if single_quotes else '<body class="existing-tool-page">'
    html_open = (
        "<html lang='ar' dir='rtl' data-tools-design='marshmallow-v245'>"
        if single_quotes
        else '<html lang="ar" dir="rtl">'
    )
    stale = ""
    if stale_contract:
        stale = (
            '<style id="tools-marshmallow-v245-style">/* stale-base-style */</style>'
            '<style id="tools-descendant-marshmallow-v250-style">/* stale-descendant-style */</style>'
        )
    if duplicate_descendant_style:
        stale += (
            '<style id="tools-descendant-marshmallow-v250-style">/* duplicate-one */</style>'
            '<style id="tools-descendant-marshmallow-v250-style">/* duplicate-two */</style>'
        )
    return (
        f'<!doctype html>{html_open}<head>'
        f"<title>{title}</title>"
        "<style>"
        "body{background:#071f27;color:#08272d}"
        ".quiz-panel,.question,.option,.result{background:#102f38;color:#0a3338}"
        ".option span{color:#fff}.option{border:1px solid #163f45}"
        "</style>"
        f"{stale}</head>"
        f"{body}<main><section class=\"quiz-panel\" data-quiz><h1>{title}</h1>"
        '<article class="question" data-question><h2>السؤال</h2>'
        '<p class="question-text">اختر الإجابة.</p>'
        '<div role="radiogroup">'
        '<label class="option" data-option for="answer-a">'
        '<input id="answer-a" type="radio" name="a" checked>'
        '<span class="option-text">الإجابة الأولى</span></label>'
        '<div class="choice" role="radio" aria-checked="true"><span>الإجابة الثانية</span></div>'
        "</div>"
        '<div class="result" data-result data-state="incorrect">'
        '<strong>النتيجة</strong><output>شرح النتيجة.</output></div>'
        '<button type="button" disabled>زر غير متاح</button>'
        "</article></section></main></body></html>"
    )


class ToolsDescendantMarshmallowV250Tests(unittest.TestCase):
    def make_site(self, *, stale_quiz: bool = False) -> Path:
        site = Path(tempfile.mkdtemp(prefix="tools-descendant-v252-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        for relative, title, single_quotes in (
            ("tools/index.html", "الأدوات", False),
            ("tools/quiz/index.html", "اختبار المصطلحات", True),
            ("tools/glossary/index.html", "المصطلحات", False),
            ("tools/deep/example/index.html", "أداة فرعية", False),
        ):
            path = site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                dark_page(
                    title,
                    single_quotes=single_quotes,
                    stale_contract=stale_quiz and relative == "tools/quiz/index.html",
                ),
                encoding="utf-8",
            )
        outside = site / "outside/index.html"
        outside.parent.mkdir(parents=True)
        outside.write_text(dark_page("خارج الأدوات"), encoding="utf-8")
        return site

    def run_publisher(self, site: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), str(site)],
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def read_report(self, site: Path) -> dict:
        return json.loads(
            (site / "api/tools-descendant-marshmallow-v250.json").read_text(encoding="utf-8")
        )

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
            self.assertIn('label:has(input[type="radio"]:checked)', text)
            self.assertIn('[role="radio"][aria-checked="true"]', text)
            self.assertIn("color:inherit!important", text)
            self.assertIn("button:disabled", text)
            self.assertIn('.feedback[aria-invalid="false"]', text)
            self.assertIn('.feedback[aria-invalid="true"]', text)
            self.assertNotIn('[data-state="correct"],[aria-invalid="false"]', text)
            self.assertIn("::placeholder", text)
            self.assertIn("@media(prefers-color-scheme:dark)", text)
            self.assertIn("@media(prefers-contrast:more)", text)
            self.assertIn("@media(prefers-reduced-motion:reduce)", text)

        quiz = (site / "tools/quiz/index.html").read_text(encoding="utf-8")
        self.assertIn(
            "class='existing-tool-page tools-marshmallow-v245 tools-descendant-marshmallow-v250'",
            quiz,
        )
        self.assertIn('data-tools-design="marshmallow-v245"', quiz)
        self.assertNotIn("data-tools-design='marshmallow-v245'", quiz)
        self.assertIn(".quiz-panel", quiz)
        self.assertIn(".question", quiz)
        self.assertIn(".option", quiz)
        self.assertIn(".result", quiz)

        self.assertEqual((site / "outside/index.html").read_bytes(), outside_before)
        report = self.read_report(site)
        self.assertEqual(report["version"], 252)
        self.assertEqual(report["status"], "published")
        self.assertEqual(report["pages"], 4)
        self.assertEqual(report["child_pages"], 3)
        self.assertTrue(report["quiz_fixed"])
        self.assertTrue(report["style_replacement_enabled"])
        self.assertTrue(report["selected_states_styled"])
        self.assertTrue(report["nested_option_text_forced"])
        self.assertTrue(report["disabled_states_styled"])
        self.assertTrue(report["dark_mode_blackening_blocked"])
        self.assertTrue(report["high_contrast_supported"])
        self.assertTrue(report["reduced_motion_supported"])
        self.assertEqual(report["unstyled_pages"], [])
        self.assertIn("tools/quiz/index.html", report["routes"])

    def test_replaces_stale_base_and_descendant_style_blocks(self) -> None:
        site = self.make_site(stale_quiz=True)
        quiz_path = site / "tools/quiz/index.html"
        self.assertIn("stale-base-style", quiz_path.read_text(encoding="utf-8"))
        self.assertIn("stale-descendant-style", quiz_path.read_text(encoding="utf-8"))

        self.run_publisher(site)

        quiz = quiz_path.read_text(encoding="utf-8")
        self.assertNotIn("stale-base-style", quiz)
        self.assertNotIn("stale-descendant-style", quiz)
        self.assertEqual(quiz.count('id="tools-marshmallow-v245-style"'), 1)
        self.assertEqual(quiz.count('id="tools-descendant-marshmallow-v250-style"'), 1)
        report = self.read_report(site)
        self.assertEqual(report["mutations"]["base_styles_replaced"], 1)
        self.assertEqual(report["mutations"]["descendant_styles_replaced"], 1)

    def test_second_run_is_byte_stable_and_does_not_replace_current_styles(self) -> None:
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
        report = self.read_report(site)
        self.assertEqual(report["updated"], 0)
        self.assertEqual(report["unchanged"], 4)
        self.assertEqual(report["mutations"]["base_styles_replaced"], 0)
        self.assertEqual(report["mutations"]["descendant_styles_replaced"], 0)

    def test_all_declared_text_background_pairs_pass_wcag_aa(self) -> None:
        publisher = load_publisher()
        contract = publisher.contrast_contract()
        self.assertTrue(contract["passes_wcag_aa_normal_text"])
        self.assertGreaterEqual(contract["minimum_ratio"], 5.2)
        self.assertGreaterEqual(len(contract["pairs"]), 25)
        for name, ratio in contract["pairs"].items():
            with self.subTest(pair=name):
                self.assertGreaterEqual(ratio, 4.5)

    def test_duplicate_descendant_style_is_rejected(self) -> None:
        site = self.make_site()
        page = site / "tools/quiz/index.html"
        page.write_text(
            dark_page("اختبار المصطلحات", duplicate_descendant_style=True),
            encoding="utf-8",
        )
        completed = self.run_publisher(site, check=False)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "Duplicate style block found: tools-descendant-marshmallow-v250-style",
            completed.stderr + completed.stdout,
        )

    def test_missing_quiz_page_is_rejected(self) -> None:
        site = self.make_site()
        (site / "tools/quiz/index.html").unlink()
        completed = self.run_publisher(site, check=False)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("tools/quiz/index.html: missing page", completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
