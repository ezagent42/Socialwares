#!/usr/bin/env python3
"""OpenAI Agents SDK adapter."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class CodexAdapter(BaseAdapter):
    """OpenAI Agents SDK adapter."""

    def launch_shell(self) -> None:
        import subprocess
        subprocess.run(["codex", "--project-dir", str(self.config.project_dir)])

    def launch_sdk(self) -> None:
        print(f"[Codex SDK] Mock — would launch {self.config.name}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    CodexAdapter(config).launch_sdk()
