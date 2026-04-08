#!/usr/bin/env python3
"""Kimi Code adapter.

Kimi Code has no standalone SDK. SDK mode is not supported.
TUI mode works via kimi CLI.

Reference:
- CLI: https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class KimiCodeAdapter(BaseAdapter):
    """Kimi Code CLI adapter. No SDK support."""

    def launch_shell(self) -> None:
        """Launch via Kimi CLI."""
        import subprocess
        subprocess.run([
            "kimi",
            "--work-dir", str(self.config.project_dir),
            "--yolo",
        ])

    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """Not supported — Kimi Code has no SDK."""
        raise NotImplementedError(
            "Kimi Code has no SDK. Use TUI mode: make start ROLE=<role> ADAPTER=kimi"
        )
        # Make it a generator for type compatibility
        if False:
            yield


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    KimiCodeAdapter(config).launch_shell()
