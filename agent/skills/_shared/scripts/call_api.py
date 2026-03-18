#!/usr/bin/env python3
"""Generic API call script for Socialware skills.

Usage:
  uv run call_api.py --config ../taskarena/config.yaml --method GET --path /tasks
  uv run call_api.py --config ../taskarena/config.yaml --method POST --path /tasks --data '{"title":"test"}'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import load_skill_config
from sw_client import create_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Call Socialware App API")
    parser.add_argument("--config", required=True, help="Path to skill config.yaml")
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--path", required=True, help="API path")
    parser.add_argument("--data", help="JSON request body")
    args = parser.parse_args()

    config = load_skill_config(Path(args.config).parent)
    client = create_client(config)

    data = json.loads(args.data) if args.data else None
    result = client.request(args.method, args.path, data)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
