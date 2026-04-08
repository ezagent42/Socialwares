#!/usr/bin/env python3
"""Save an improve report after evolver applies changes.

The evolver LLM calls this script to persist its improvement decisions.
Other evolver scripts save reports automatically; improve is LLM-driven,
so the LLM must explicitly call this script with the change details.

Usage:
    uv run save_report.py --change '{"primitive":"flow","file":"agent/flow/create_task/SKILL.md","action":"Updated trigger","reason":"40% error rate"}'
    uv run save_report.py --change '...' --change '...' --based-on diagnose_20250326.json --next-step "Run evaluate"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    # Find workspace root
    workspace_root_file = Path(".workspace_root")
    if workspace_root_file.exists():
        workspace_root = Path(workspace_root_file.read_text().strip())
        os.chdir(workspace_root)

    parser = argparse.ArgumentParser(description="Save improve report")
    parser.add_argument(
        "--change", action="append", required=True,
        help="JSON object: {primitive, file, action, reason}. Can repeat.",
    )
    parser.add_argument(
        "--based-on", action="append", default=[],
        help="Report file(s) that informed this improvement. Can repeat.",
    )
    parser.add_argument(
        "--next-step", default="Run 'evaluate' to check if score improved",
        help="Suggested next step after this improvement.",
    )
    args = parser.parse_args()

    # Parse changes
    changes = []
    for raw in args.change:
        try:
            changes.append(json.loads(raw))
        except json.JSONDecodeError:
            # Accept simple string as action description
            changes.append({"action": raw})

    # Save report (only if .runtime/ exists)
    if not Path(".runtime").exists():
        print("No .runtime/ directory — skipping report save.")
        sys.exit(0)

    report_dir = Path(".runtime/data/evolve/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    report_file = report_dir / f"improve_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"

    report_data = {
        "type": "improve",
        "timestamp": timestamp.isoformat(),
        "changes": changes,
        "based_on": args.based_on,
        "next_step": args.next_step,
    }

    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"Report saved to {report_file}")


if __name__ == "__main__":
    main()
