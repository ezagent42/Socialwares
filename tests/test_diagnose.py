"""Tests for the evolve_diagnose script."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
DIAGNOSE_SCRIPT = REPO_ROOT / "agent" / "flow" / "evolve_diagnose" / "scripts" / "diagnose.py"


class TestDiagnose:
    """Test diagnose.py script."""

    def test_script_exists(self):
        assert DIAGNOSE_SCRIPT.exists()

    def test_runs_with_empty_data(self, tmp_path):
        """Diagnose runs even with no data — reports no issues."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        constraints = tmp_path / "constraints.yaml"
        constraints.write_text("transition_constraints: {}\naction_constraints: {}\n")

        result = subprocess.run(
            [sys.executable, str(DIAGNOSE_SCRIPT),
             "--data-dir", str(data_dir),
             "--constraints", str(constraints)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "DIAGNOSTIC REPORT" in result.stdout

    def test_detects_conversation_errors(self, tmp_path):
        """Diagnose detects errors in conversation logs."""
        data_dir = tmp_path / "data"
        conv_dir = data_dir / "conversations"
        conv_dir.mkdir(parents=True)
        constraints = tmp_path / "constraints.yaml"
        constraints.write_text("transition_constraints: {}\naction_constraints: {}\n")

        # Write sample conversation with errors
        entries = [
            json.dumps({"tool": "create_task", "role": "default", "success": True}),
            json.dumps({"tool": "create_task", "role": "default", "success": False, "error": "500 Internal Error"}),
            json.dumps({"tool": "check_health", "role": "default", "success": True}),
        ]
        (conv_dir / "current.jsonl").write_text("\n".join(entries) + "\n")

        result = subprocess.run(
            [sys.executable, str(DIAGNOSE_SCRIPT),
             "--data-dir", str(data_dir),
             "--constraints", str(constraints)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Error rate" in result.stdout
        assert "create_task" in result.stdout

    def test_detects_violations(self, tmp_path):
        """Diagnose detects constraint violations."""
        data_dir = tmp_path / "data"
        viol_dir = data_dir / "violations"
        viol_dir.mkdir(parents=True)
        constraints = tmp_path / "constraints.yaml"
        constraints.write_text("transition_constraints: {}\naction_constraints: {}\n")

        entries = [
            json.dumps({"constraint": "C1", "description": "review overdue", "resolved": False}),
            json.dumps({"constraint": "C1", "description": "review overdue", "resolved": True}),
        ]
        (viol_dir / "current.jsonl").write_text("\n".join(entries) + "\n")

        result = subprocess.run(
            [sys.executable, str(DIAGNOSE_SCRIPT),
             "--data-dir", str(data_dir),
             "--constraints", str(constraints)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Unresolved: 1" in result.stdout
