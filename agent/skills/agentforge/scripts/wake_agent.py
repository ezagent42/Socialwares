#!/usr/bin/env python3
"""Wake a sleeping agent.

Usage:
  uv run wake_agent.py --name reviewer-1
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
    parser = argparse.ArgumentParser(description="Wake sleeping agent")
    parser.add_argument("--name", required=True, help="Agent name")
    args = parser.parse_args()

    config = load_skill_config(SKILL_DIR)
    client = create_client(config)

    result = client.request("POST", f"/agents/{args.name}/wake")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
