#!/usr/bin/env python3
"""Save a commitment violation after evolver judges fulfillment.

The evolver LLM calls this script after running diagnose + judging conditions.
Violations are stored as JSONL in .runtime/data/evolve/violations/ and
served via the app's GET /violations API.

Usage:
    uv run save_violation.py --commitment C1 --description "review overdue" --role reviewer
    uv run save_violation.py --commitment C1 --description "review overdue" --role reviewer --action review_task
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    # Find workspace root
    workspace_root_file = Path(".workspace_root")
    if workspace_root_file.exists():
        workspace_root = Path(workspace_root_file.read_text().strip())
        os.chdir(workspace_root)

    parser = argparse.ArgumentParser(description="Save a commitment violation")
    parser.add_argument("--commitment", required=True, help="Commitment ID (e.g. C1)")
    parser.add_argument("--description", required=True, help="What was violated")
    parser.add_argument("--role", required=True, help="Which role is responsible")
    parser.add_argument("--action", default="", help="Which action was involved")
    parser.add_argument("--evidence", default="", help="Evidence from diagnose report (timestamps, counts)")
    args = parser.parse_args()

    # Save violation (only if .runtime/ exists)
    if not Path(".runtime").exists():
        print("No .runtime/ directory — skipping violation save.")
        sys.exit(0)

    violations_dir = Path(".runtime/data/evolve/violations")
    violations_dir.mkdir(parents=True, exist_ok=True)
    violations_file = violations_dir / "current.jsonl"

    violation = {
        "id": f"v-{uuid.uuid4().hex[:8]}",
        "commitment": args.commitment,
        "description": args.description,
        "role": args.role,
        "action": args.action,
        "evidence": args.evidence,
        "resolved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(violations_file, "a") as f:
        f.write(json.dumps(violation, ensure_ascii=False) + "\n")

    print(f"Violation saved: {violation['id']}")
    print(f"  Commitment: {args.commitment}")
    print(f"  Description: {args.description}")
    print(f"  File: {violations_file}")


if __name__ == "__main__":
    main()
