#!/usr/bin/env python3
"""Claude Code launcher — cross-platform replacement for shell.sh.

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
    os.chdir(project_dir)

    claude = shutil.which("claude")
    if not claude:
        print("Error: 'claude' not found in PATH. Install Claude Code first.", file=sys.stderr)
        sys.exit(1)

    args = [claude, "--dangerously-skip-permissions"]

    soul_md = project_dir / "SOUL.md"
    if soul_md.is_file():
        args.extend(["--append-system-prompt-file", "SOUL.md"])

    os.execv(claude, args)


if __name__ == "__main__":
    main()
