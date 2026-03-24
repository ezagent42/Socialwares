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
        commitment = tmp_path / "commitment.yaml"
        commitment.write_text("commitments: {}\n")

        result = subprocess.run(
            [sys.executable, str(DIAGNOSE_SCRIPT),
             "--data-dir", str(data_dir),
             "--commitment", str(commitment)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "DIAGNOSTIC REPORT" in result.stdout

    def test_runs_with_prompt_data(self, tmp_path):
        """Diagnose reads hook prompt logs."""
        data_dir = tmp_path / "data"
        prompts_dir = data_dir / "prompts"
        prompts_dir.mkdir(parents=True)
        commitment = tmp_path / "commitment.yaml"
        commitment.write_text("commitments: {}\n")

        entries = [
            json.dumps({"type": "user_prompt", "role": "default", "content": "check health", "timestamp": "2026-03-24T10:00:00Z"}),
            json.dumps({"type": "tool_call", "role": "default", "tool": "Bash", "input": {"command": "curl /health"}, "timestamp": "2026-03-24T10:00:05Z"}),
        ]
        (prompts_dir / "current.jsonl").write_text("\n".join(entries) + "\n")

        result = subprocess.run(
            [sys.executable, str(DIAGNOSE_SCRIPT),
             "--data-dir", str(data_dir),
             "--commitment", str(commitment)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Hook log entries: 2" in result.stdout

    def test_commitment_fulfillment(self, tmp_path):
        """Diagnose computes fulfillment rate for commitments."""
        data_dir = tmp_path / "data"
        prompts_dir = data_dir / "prompts"
        prompts_dir.mkdir(parents=True)

        commitment = tmp_path / "commitment.yaml"
        commitment.write_text("""
commitments:
  C1:
    from: { role: coder, action: submit_code }
    to: { role: pm, action: review_code }
    condition: "within 24h"
""")

        entries = [
            json.dumps({"type": "user_prompt", "role": "coder", "content": "submit code for review", "timestamp": "2026-03-24T10:00:00Z"}),
            json.dumps({"type": "user_prompt", "role": "pm", "content": "review code submission", "timestamp": "2026-03-24T12:00:00Z"}),
        ]
        (prompts_dir / "current.jsonl").write_text("\n".join(entries) + "\n")

        result = subprocess.run(
            [sys.executable, str(DIAGNOSE_SCRIPT),
             "--data-dir", str(data_dir),
             "--commitment", str(commitment)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "C1" in result.stdout
        assert "submit_code" in result.stdout
        assert "review_code" in result.stdout
