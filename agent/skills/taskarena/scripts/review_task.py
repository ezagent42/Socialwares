#!/usr/bin/env python3
"""Review a task in TaskArena.

Usage:
  uv run review_task.py --id task-001 --decision approve
  uv run review_task.py --id task-001 --decision reject --reason "缺售后条款"
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
    parser = argparse.ArgumentParser(description="Review TaskArena task")
    parser.add_argument("--id", required=True, help="Task ID")
    parser.add_argument("--decision", required=True, choices=["approve", "reject"])
    parser.add_argument("--reason", help="Review reason (required for reject)")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    data = {"decision": args.decision}
    if args.reason:
        data["reason"] = args.reason

    result = client.request("POST", f"/tasks/{args.id}/review", data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
