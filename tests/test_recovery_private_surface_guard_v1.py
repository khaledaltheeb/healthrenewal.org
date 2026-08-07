#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'recover_content_full_history_v3.py'


def load_module():
    spec = importlib.util.spec_from_file_location('recover_content_full_history_v3', SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_obsolete_professional_assessment_prototype_is_not_resurrected_from_history():
    module = load_module()
    assert module.recovery_safe('professional-assessment-hub/index.html') is False
    assert module.recovery_safe('/professional-assessment-hub/styles.css') is False
    assert module.recovery_safe('professional-assessment-hub/app.js') is False


def test_public_editorial_routes_remain_recoverable():
    module = load_module()
    assert module.recovery_safe('terms/anxiety/index.html') is True
    assert module.recovery_safe('special-needs/index.html') is True
