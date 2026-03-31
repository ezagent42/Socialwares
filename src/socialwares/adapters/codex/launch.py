#!/usr/bin/env python3
"""Codex CLI launcher — cross-platform replacement for shell.sh.

Usage: python launch.py <project_dir>
"""
import os
import shutil
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: launch.py <project_dir>", file=sys.stderr)
        sys.exit(1)

    project_dir = Path(sys.argv[1]).resolve()

    codex = shutil.which("codex")
    if not codex:
        print("Error: 'codex' not found in PATH. Install Codex CLI first.", file=sys.stderr)
        sys.exit(1)

    os.execv(codex, [codex, "--cd", str(project_dir), "--full-auto"])


if __name__ == "__main__":
    main()
