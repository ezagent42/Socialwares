#!/usr/bin/env python3
"""Query tasks from TaskArena.

Usage:
  uv run query_task.py                    # list all
  uv run query_task.py --id task-001      # get one
  uv run query_task.py --status submitted # filter by status
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
    parser = argparse.ArgumentParser(description="Query TaskArena tasks")
    parser.add_argument("--id", help="Task ID (get one)")
    parser.add_argument("--status", help="Filter by status")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    if args.id:
        result = client.request("GET", f"/tasks/{args.id}")
    elif args.status:
        result = client.request("GET", f"/tasks?status={args.status}")
    else:
        result = client.request("GET", "/tasks")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
