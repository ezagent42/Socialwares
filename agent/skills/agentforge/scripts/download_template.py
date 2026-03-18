#!/usr/bin/env python3
"""Download agent template from registry.

Usage:
  uv run download_template.py --source "github:ezagent42/templates/code-reviewer"
  uv run download_template.py --source "local:templates/task-worker"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config

SKILL_DIR = Path(__file__).parent.parent
AGENTS_DIR = SKILL_DIR.parent.parent / "agents"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download agent template")
    parser.add_argument("--source", required=True, help="Template source (github:org/repo/name or local:path)")
    parser.add_argument("--target", help="Target directory name (default: template name)")
    args = parser.parse_args()

    # Parse source
    if args.source.startswith("github:"):
        parts = args.source[7:].split("/")
        template_name = parts[-1] if not args.target else args.target
        print(f"TODO: Download from GitHub — {args.source}")
        print(f"Target: {AGENTS_DIR / template_name}")
    elif args.source.startswith("local:"):
        local_path = Path(args.source[6:])
        template_name = local_path.name if not args.target else args.target
        print(f"TODO: Copy from local — {local_path}")
        print(f"Target: {AGENTS_DIR / template_name}")
    else:
        print(f"Unknown source format: {args.source}", file=sys.stderr)
        sys.exit(1)

    result = {
        "action": "download_template",
        "source": args.source,
        "target": str(AGENTS_DIR / template_name),
        "status": "mock — not implemented yet",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
