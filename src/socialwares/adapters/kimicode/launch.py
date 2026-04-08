#!/usr/bin/env python3
"""Kimi Code CLI launcher — cross-platform replacement for shell.sh.

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

    kimi = shutil.which("kimi")
    if not kimi:
        print("Error: 'kimi' not found in PATH. Install Kimi Code CLI first.", file=sys.stderr)
        sys.exit(1)

    os.execv(kimi, [kimi, "--work-dir", str(project_dir), "--yolo"])


if __name__ == "__main__":
    main()
