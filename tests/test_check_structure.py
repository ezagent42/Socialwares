"""Tests for the evolve_check structure checking script."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
CHECK_SCRIPT = REPO_ROOT / "agent" / "flow" / "evolve_check" / "scripts" / "check_structure.py"


class TestCheckStructure:
    """Test check_structure.py script."""

    def test_script_exists(self):
        assert CHECK_SCRIPT.exists()

    def test_template_passes(self):
        """Template's own four primitives should pass structure check."""
        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT),
             "--agent-dir", str(REPO_ROOT / "agent")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_detects_missing_skill(self, tmp_path):
        """Should detect action in flow.yaml without SKILL.md."""
        agent_dir = tmp_path / "agent"
        (agent_dir / "flow").mkdir(parents=True)
        (agent_dir / "role").mkdir()
        (agent_dir / "scope").mkdir()
        (agent_dir / "commitment").mkdir()

        # flow.yaml with action but no SKILL.md directory
        (agent_dir / "flow" / "flow.yaml").write_text("""
direct_actions:
  - { action: missing_skill, role: [default], description: "No SKILL.md" }
""")
        (agent_dir / "role" / "default.md").write_text("# Default")
        (agent_dir / "scope" / "scope.md").write_text("# Scope")
        (agent_dir / "commitment" / "commitment.yaml").write_text("commitments: {}")

        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT),
             "--agent-dir", str(agent_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "MISSING SKILL" in result.stdout
        assert "missing_skill" in result.stdout

    def test_detects_missing_commitment_role(self, tmp_path):
        """Should detect commitment referencing non-existent role."""
        agent_dir = tmp_path / "agent"
        (agent_dir / "flow").mkdir(parents=True)
        (agent_dir / "role").mkdir()
        (agent_dir / "scope").mkdir()
        (agent_dir / "commitment").mkdir()

        (agent_dir / "flow" / "flow.yaml").write_text("direct_actions: []")
        (agent_dir / "role" / "default.md").write_text("# Default")
        (agent_dir / "scope" / "scope.md").write_text("# Scope")
        (agent_dir / "commitment" / "commitment.yaml").write_text("""
commitments:
  C1:
    from: { role: nonexistent, action: submit }
    to: { role: default, action: review }
    condition: "within 24h"
""")

        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT),
             "--agent-dir", str(agent_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "nonexistent" in result.stdout
