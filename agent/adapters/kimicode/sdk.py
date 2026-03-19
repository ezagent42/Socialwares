#!/usr/bin/env python3
"""Kimi Code SDK adapter.

Reference:
- CLI: https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class KimiCodeAdapter(BaseAdapter):
    """Kimi Code CLI adapter."""

    def launch_shell(self) -> None:
        """Launch via Kimi CLI."""
        subprocess.run([
            "kimi",
            "--work-dir", str(self.config.project_dir),
            "--yolo",
        ])

    def launch_sdk(self) -> None:
        """Kimi Code has no standalone SDK yet; falls back to CLI."""
        print(f"[Kimi] Launching {self.config.name} via CLI")
        self.launch_shell()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    KimiCodeAdapter(config).launch_shell()
