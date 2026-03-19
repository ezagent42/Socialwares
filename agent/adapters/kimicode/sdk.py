#!/usr/bin/env python3
"""KimiCode SDK adapter."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class KimiCodeAdapter(BaseAdapter):
    """KimiCode SDK adapter."""

    def launch_shell(self) -> None:
        print(f"[KimiCode] Shell mode not available yet")

    def launch_sdk(self) -> None:
        print(f"[KimiCode SDK] Mock — would launch {self.config.name}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    KimiCodeAdapter(config).launch_sdk()
