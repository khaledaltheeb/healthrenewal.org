from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
JS = SITE / "assets/js/lab-v12.js"
PARTS = Path(__file__).with_name("v212_difficulty_parts")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"Missing v212 patch target: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    if not JS.exists():
        raise SystemExit(f"Missing cognitive runtime: {JS}")
    part_files = sorted(PARTS.glob("part*.jsfrag"))
    if len(part_files) != 5:
        raise SystemExit(f"Expected 5 v212 difficulty fragments, found {len(part_files)}")
    difficulty_function = "".join(path.read_text(encoding="utf-8") for path in part_files)
    if "function v212DifficultyData(" not in difficulty_function:
        raise SystemExit("Invalid v212 difficulty fragments")
    text = JS.read_text(encoding="utf-8")
    if "function v212DifficultyData(" not in text:
        text = replace_once(text, "function v211BankData(", difficulty_function + "\nfunction v211BankData(", "v211 bank function")
    old_hook = "const bankV211=v211BankData(d,stage,index,sessionSeed,rnd,ri,pick,symbols,arrows);if(bankV211)return v202Finish(d,stage,rnd,bankV211);"
    new_hook = "const gradedV212=v212DifficultyData(d,stage,index,sessionSeed,rnd,ri,pick,symbols,arrows);if(gradedV212)return v202Finish(d,stage,rnd,gradedV212);const bankV211=v211BankData(d,stage,index,sessionSeed,rnd,ri,pick,symbols,arrows);if(bankV211)return v202Finish(d,stage,rnd,bankV211);"
    text = replace_once(text, old_hook, new_hook, "v212 generator hook")
    JS.write_text(text, encoding="utf-8")
    report = {
        "version": 212,
        "status": "built-not-published",
        "graded_modes": [
            "choice_reaction", "visual_reaction", "response_inhibition", "conditional_reasoning",
            "context_clues", "emotion_recognition", "perspective_taking", "planning_steps",
            "priority_planning", "problem_solving", "word_categories", "semantic_fluency",
            "social_scenarios", "verbal_analogy",
        ],
        "graded_mode_count": 14,
        "five_stage_progression": True,
        "actual_task_parameters": True,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "cognitive-difficulty-v212.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
