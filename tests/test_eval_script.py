"""Tests for the evolve_eval run_eval.py script."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
EVAL_SCRIPT = REPO_ROOT / "agent" / "flow" / "evolve_eval" / "scripts" / "run_eval.py"
EVAL_CASES = REPO_ROOT / "agent" / "flow" / "evolve_eval" / "eval_cases.yaml"


class TestEvalScript:
    """Test run_eval.py script."""

    def test_script_exists(self):
        assert EVAL_SCRIPT.exists()

    def test_eval_cases_exists(self):
        assert EVAL_CASES.exists()

    def test_runs_with_eval_cases(self, tmp_path):
        """Eval runs with the template eval_cases.yaml (may fail if app not running)."""
        result = subprocess.run(
            [sys.executable, str(EVAL_SCRIPT),
             "--cases", str(EVAL_CASES),
             "--base-url", "http://localhost:99999"],  # intentionally wrong port
            capture_output=True, text=True,
        )
        # Should complete (not crash) even if app is not running
        assert result.returncode == 0
        assert "Score:" in result.stdout

    def test_runs_with_custom_cases(self, tmp_path):
        """Eval runs with custom cases file."""
        cases_file = tmp_path / "cases.yaml"
        cases_file.write_text("""cases:
  - description: "Test endpoint"
    method: GET
    endpoint: /nonexistent
    expected_status: 200
""")
        result = subprocess.run(
            [sys.executable, str(EVAL_SCRIPT),
             "--cases", str(cases_file),
             "--base-url", "http://localhost:99999"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Score:" in result.stdout

    def test_api_only_no_conversation_checks(self, tmp_path):
        """eval_cases.yaml should only contain api_checks, no conversation_checks."""
        import yaml
        with open(EVAL_CASES) as f:
            data = yaml.safe_load(f) or {}
        assert "api_checks" in data
        assert "conversation_checks" not in data
