#!/usr/bin/env python3
"""Create a task in TaskArena.

Usage:
  uv run create_task.py --title "GPS采购" --budget 300000
  uv run create_task.py --title "代码审查" --assignee bob
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
    parser = argparse.ArgumentParser(description="Create TaskArena task")
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--budget", type=float, help="Budget amount")
    parser.add_argument("--assignee", help="Assignee identity")
    parser.add_argument("--description", help="Task description")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    data = {"title": args.title, "status": "draft"}
    if args.budget:
        data["budget"] = args.budget
    if args.assignee:
        data["assignee"] = args.assignee
    if args.description:
        data["description"] = args.description

    result = client.request("POST", "/tasks", data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
