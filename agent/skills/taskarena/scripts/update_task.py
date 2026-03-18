#!/usr/bin/env python3
"""Update a task in TaskArena.

Usage:
  uv run update_task.py --id task-001 --status under_review
  uv run update_task.py --id task-001 --title "Updated title"
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
    parser = argparse.ArgumentParser(description="Update TaskArena task")
    parser.add_argument("--id", required=True, help="Task ID")
    parser.add_argument("--status", help="New status")
    parser.add_argument("--title", help="New title")
    parser.add_argument("--assignee", help="New assignee")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    data: dict = {}
    if args.status:
        data["status"] = args.status
    if args.title:
        data["title"] = args.title
    if args.assignee:
        data["assignee"] = args.assignee

    result = client.request("PUT", f"/tasks/{args.id}", data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
