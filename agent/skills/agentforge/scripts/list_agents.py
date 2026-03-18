#!/usr/bin/env python3
"""List all agents.

Usage:
  uv run list_agents.py
  uv run list_agents.py --status active
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
    parser = argparse.ArgumentParser(description="List AgentForge agents")
    parser.add_argument("--status", help="Filter by status")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    path = "/agents"
    if args.status:
        path += f"?status={args.status}"

    result = client.request("GET", path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
