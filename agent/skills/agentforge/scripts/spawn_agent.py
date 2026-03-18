#!/usr/bin/env python3
"""Spawn an agent from template.

Usage:
  uv run spawn_agent.py --template code-reviewer --name reviewer-1
  uv run spawn_agent.py --template code-reviewer --name reviewer-1 --adapter codex
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "_shared"))
from config import load_skill_config
from sw_client import create_client

SKILL_DIR = Path(__file__).parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Spawn agent from template")
    parser.add_argument("--template", required=True, help="Template name")
    parser.add_argument("--name", required=True, help="Agent instance name")
    parser.add_argument("--adapter", default="claude", choices=["claude", "codex", "kimicode"])
    parser.add_argument("--parent", help="Parent agent name")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    data = {
        "template": args.template,
        "name": args.name,
        "adapter": args.adapter,
    }
    if args.parent:
        data["parent"] = args.parent

    result = client.request("POST", "/agents/spawn", data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
