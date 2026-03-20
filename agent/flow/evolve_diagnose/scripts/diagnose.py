#!/usr/bin/env python3
"""Diagnose issues from Socialware App runtime data.

Scans multiple data sources to find improvement opportunities:
- Conversations: failed actions, missing capabilities, scope violations
- Violations: constraint violations and frequency
- Constraints: active constraint summary

Usage:
    uv run diagnose.py --data-dir .runtime/data --constraints agent/commitment/constraints.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml


def scan_conversations(data_dir: Path) -> dict:
    """Scan conversation logs for patterns."""
    conv_dir = data_dir / "conversations"
    if not conv_dir.exists():
        return {"total": 0, "errors": [], "tools": Counter()}

    total = 0
    errors = []
    tools = Counter()
    roles = Counter()

    for f in conv_dir.glob("*.jsonl"):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                total += 1
                tool = entry.get("tool", entry.get("action", "unknown"))
                tools[tool] += 1
                role = entry.get("role", "unknown")
                roles[role] += 1

                # Detect errors
                if entry.get("success") is False or entry.get("error"):
                    errors.append({
                        "tool": tool,
                        "error": entry.get("error", "unknown error"),
                        "role": role,
                    })
            except json.JSONDecodeError:
                continue

    return {
        "total": total,
        "errors": errors,
        "tools": dict(tools.most_common(20)),
        "roles": dict(roles),
        "error_rate": len(errors) / total if total > 0 else 0,
    }


def scan_violations(data_dir: Path) -> dict:
    """Scan violation logs."""
    viol_dir = data_dir / "violations"
    if not viol_dir.exists():
        return {"total": 0, "unresolved": 0, "by_constraint": {}}

    total = 0
    unresolved = 0
    by_constraint = Counter()

    for f in viol_dir.glob("*.jsonl"):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                v = json.loads(line)
                total += 1
                if not v.get("resolved", False):
                    unresolved += 1
                by_constraint[v.get("constraint", "unknown")] += 1
            except json.JSONDecodeError:
                continue

    return {
        "total": total,
        "unresolved": unresolved,
        "by_constraint": dict(by_constraint),
    }


def load_constraints(path: Path) -> dict:
    """Load active constraints summary."""
    if not path.exists():
        return {"transition": 0, "action": 0, "constraints": []}

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    transition = data.get("transition_constraints") or {}
    action = data.get("action_constraints") or {}

    constraints = []
    for cid, c in (transition.items() if isinstance(transition, dict) else []):
        constraints.append({"id": cid, "type": "transition", "description": c.get("description", "")})
    for cid, c in (action.items() if isinstance(action, dict) else []):
        constraints.append({"id": cid, "type": "action", "description": c.get("description", "")})

    return {
        "transition": len(transition) if isinstance(transition, dict) else 0,
        "action": len(action) if isinstance(action, dict) else 0,
        "constraints": constraints,
    }


def generate_report(conversations: dict, violations: dict, constraints: dict) -> str:
    """Generate human-readable diagnostic report."""
    lines = []
    lines.append("=" * 60)
    lines.append("DIAGNOSTIC REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Conversations
    lines.append("## Conversations")
    lines.append(f"  Total interactions: {conversations['total']}")
    lines.append(f"  Error rate: {conversations['error_rate']:.1%}")
    if conversations["tools"]:
        lines.append(f"  Top tools: {', '.join(f'{k}({v})' for k, v in list(conversations['tools'].items())[:5])}")
    if conversations["roles"]:
        lines.append(f"  Active roles: {', '.join(conversations['roles'].keys())}")
    if conversations["errors"]:
        lines.append(f"  Errors ({len(conversations['errors'])}):")
        for err in conversations["errors"][:5]:
            lines.append(f"    - [{err['role']}] {err['tool']}: {err['error']}")
    lines.append("")

    # Violations
    lines.append("## Constraint Violations")
    lines.append(f"  Total: {violations['total']}")
    lines.append(f"  Unresolved: {violations['unresolved']}")
    if violations["by_constraint"]:
        lines.append(f"  By constraint: {dict(violations['by_constraint'])}")
    lines.append("")

    # Constraints
    lines.append("## Active Constraints")
    lines.append(f"  Transition constraints: {constraints['transition']}")
    lines.append(f"  Action constraints: {constraints['action']}")
    for c in constraints["constraints"]:
        lines.append(f"    [{c['id']}] ({c['type']}) {c['description']}")
    lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    if conversations["error_rate"] > 0.1:
        lines.append("  [Flow] High error rate — review failing skills")
    if violations["unresolved"] > 0:
        lines.append("  [Commitment] Unresolved violations — check constraint deadlines")
    if conversations["total"] == 0:
        lines.append("  [Info] No conversation data yet — use the app first")
    if not conversations["errors"] and violations["total"] == 0:
        lines.append("  [OK] No issues found")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose Socialware App issues")
    parser.add_argument("--data-dir", default=".runtime/data", help="Runtime data directory")
    parser.add_argument("--constraints", default="agent/commitment/constraints.yaml", help="Constraints file")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    constraints_path = Path(args.constraints)

    conversations = scan_conversations(data_dir)
    violations = scan_violations(data_dir)
    constraints = load_constraints(constraints_path)

    report = generate_report(conversations, violations, constraints)
    print(report)

    # Save report for evolver to read
    report_file = data_dir / "last_diagnosis.txt"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report)
    print(f"Report saved to {report_file}")


if __name__ == "__main__":
    main()
