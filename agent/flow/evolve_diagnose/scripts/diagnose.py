#!/usr/bin/env python3
"""Diagnose — analyze conversation data against commitment standards.

Reads hook logs (prompts/*.jsonl) and SDK sessions (sessions/*.json),
checks each commitment's fulfillment, computes rates, updates cursor.

Usage:
    uv run diagnose.py --data-dir .runtime/data --commitment agent/commitment/commitment.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_commitment(path: Path) -> dict:
    """Load commitment definitions."""
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("commitments", {})


def load_cursor(data_dir: Path) -> dict:
    """Load evolve/state.yaml cursor."""
    state_file = data_dir / "evolve" / "state.yaml"
    if not state_file.exists():
        return {}
    with open(state_file) as f:
        return yaml.safe_load(f) or {}


def save_cursor(data_dir: Path, state: dict) -> None:
    """Save evolve/state.yaml."""
    state_file = data_dir / "evolve" / "state.yaml"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w") as f:
        yaml.dump(state, f, default_flow_style=False)


def scan_prompts(data_dir: Path, cursor: dict) -> list[dict]:
    """Read hook prompt logs (JSONL), filtering by cursor."""
    prompts_dir = data_dir / "prompts"
    if not prompts_dir.exists():
        return []

    entries = []
    cursor_line = cursor.get("prompts_line", 0)
    current_line = 0

    for f in sorted(prompts_dir.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            current_line += 1
            if current_line <= cursor_line:
                continue
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return entries


def scan_sessions(data_dir: Path, cursor: dict) -> list[dict]:
    """Read SDK session files, filtering by cursor."""
    sessions_dir = data_dir / "sessions"
    if not sessions_dir.exists():
        return []

    sessions = []
    cursor_file = cursor.get("sessions_cursor", "")

    for f in sorted(sessions_dir.glob("*.json")):
        if cursor_file and f.name <= cursor_file:
            continue
        try:
            with open(f) as fh:
                sessions.append(json.load(fh))
        except (json.JSONDecodeError, IOError):
            continue

    return sessions


def analyze_commitment_fulfillment(
    commitments: dict,
    prompt_entries: list[dict],
    sessions: list[dict],
) -> dict:
    """Analyze fulfillment rate per commitment.

    For each commitment, looks for from.action and to.action events
    in the data, then checks if condition was met.
    """
    results = {}

    for cid, c in commitments.items():
        from_action = c.get("from", {}).get("action", "")
        to_action = c.get("to", {}).get("action", "")
        condition = c.get("condition", "")

        # Find from/to events in prompt data
        from_events = []
        to_events = []

        for entry in prompt_entries:
            content = entry.get("content", "")
            tool = entry.get("tool", "")
            tool_input = entry.get("input", {})

            # Match by action name appearing in prompt or tool input
            text = f"{content} {tool} {json.dumps(tool_input)}"
            if from_action and from_action.replace("_", " ") in text.lower():
                from_events.append(entry)
            if to_action and to_action.replace("_", " ") in text.lower():
                to_events.append(entry)

        # Also check SDK sessions
        for session in sessions:
            for msg in session.get("messages", []):
                msg_text = json.dumps(msg)
                if from_action and from_action.replace("_", " ") in msg_text.lower():
                    from_events.append({"timestamp": session.get("started_at", ""), **msg})
                if to_action and to_action.replace("_", " ") in msg_text.lower():
                    to_events.append({"timestamp": session.get("started_at", ""), **msg})

        # Calculate fulfillment
        total = len(from_events)
        fulfilled = min(len(to_events), total)  # can't fulfill more than triggered

        results[cid] = {
            "from_action": from_action,
            "to_action": to_action,
            "condition": condition,
            "triggered": total,
            "fulfilled": fulfilled,
            "rate": fulfilled / total if total > 0 else None,
        }

    return results


def generate_report(
    commitments: dict,
    fulfillment: dict,
    prompt_count: int,
    session_count: int,
) -> str:
    """Generate diagnostic report."""
    lines = []
    lines.append("=" * 60)
    lines.append("DIAGNOSTIC REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Data summary
    lines.append("## Data Sources")
    lines.append(f"  Hook log entries: {prompt_count}")
    lines.append(f"  SDK sessions: {session_count}")
    lines.append("")

    # Commitment fulfillment
    lines.append("## Commitment Fulfillment")
    if not fulfillment:
        lines.append("  No commitments defined.")
    else:
        for cid, result in fulfillment.items():
            rate = result["rate"]
            if rate is None:
                rate_str = "N/A (no events)"
            else:
                rate_str = f"{rate:.0%}"
            lines.append(f"  [{cid}] {result['from_action']} → {result['to_action']}")
            lines.append(f"         condition: {result['condition']}")
            lines.append(f"         triggered: {result['triggered']}, fulfilled: {result['fulfilled']}, rate: {rate_str}")
    lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    has_issues = False
    for cid, result in fulfillment.items():
        if result["rate"] is not None and result["rate"] < 0.8:
            has_issues = True
            lines.append(f"  [Commitment] {cid} fulfillment rate {result['rate']:.0%} — consider improving flow or adjusting standard")
        if result["triggered"] == 0:
            has_issues = True
            lines.append(f"  [Info] {cid} never triggered — is from.action '{result['from_action']}' being used?")
    if prompt_count == 0 and session_count == 0:
        has_issues = True
        lines.append("  [Info] No conversation data yet — use the app first")
    if not has_issues:
        lines.append("  [OK] No issues found")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def main() -> None:
    # Find workspace root
    workspace_root_file = Path(".workspace_root")
    if workspace_root_file.exists():
        workspace_root = Path(workspace_root_file.read_text().strip())
        os.chdir(workspace_root)

    parser = argparse.ArgumentParser(description="Diagnose Socialware App")
    parser.add_argument("--data-dir", default=".runtime/data", help="Runtime data directory")
    parser.add_argument("--commitment", default="agent/commitment/commitment.yaml", help="Commitment file")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    commitment_path = Path(args.commitment)

    # Load
    commitments = load_commitment(commitment_path)
    cursor = load_cursor(data_dir)

    # Scan data
    prompt_entries = scan_prompts(data_dir, cursor)
    sessions = scan_sessions(data_dir, cursor)

    # Analyze
    fulfillment = analyze_commitment_fulfillment(commitments, prompt_entries, sessions)

    # Report
    report = generate_report(commitments, fulfillment, len(prompt_entries), len(sessions))
    print(report)

    # Compute average fulfillment rate
    rated = [r["rate"] for r in fulfillment.values() if r["rate"] is not None]
    avg_rate = sum(rated) / len(rated) if rated else 0.0

    # Build recommendations for suggestions
    suggestions = []
    for cid, result in fulfillment.items():
        if result["rate"] is not None and result["rate"] < 0.8:
            suggestions.append({
                "primitive": "commitment",
                "action": f"Improve fulfillment for {cid}",
                "reason": f"Fulfillment rate {result['rate']:.0%} — below 80% threshold",
            })
        if result["triggered"] == 0:
            suggestions.append({
                "primitive": "flow",
                "action": f"Check if from.action '{result['from_action']}' is being used",
                "reason": f"{cid} never triggered",
            })

    # Save report as JSON
    report_dir = data_dir / "evolve" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    report_file = report_dir / f"diagnose_{timestamp_str}.json"

    report_data = {
        "type": "diagnose",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "prompts/*.jsonl + sessions/*.json",
        "score": avg_rate,
        "passed": sum(1 for r in fulfillment.values() if r["rate"] is not None and r["rate"] >= 0.8),
        "total": len(fulfillment),
        "summary": report,
        "details": fulfillment,
        "suggestions": suggestions,
    }
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"Report saved to {report_file}")

    # Update cursor
    new_state = {
        "last_analysis": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompts_line": cursor.get("prompts_line", 0) + len(prompt_entries),
            "sessions_cursor": sorted(
                (data_dir / "sessions").glob("*.json")
            )[-1].name if (data_dir / "sessions").exists() and list((data_dir / "sessions").glob("*.json")) else "",
            "results": {
                "fulfillment": {
                    cid: {"fulfilled": r["fulfilled"], "total": r["triggered"], "rate": r["rate"]}
                    for cid, r in fulfillment.items()
                },
            },
        },
    }
    save_cursor(data_dir, new_state)


if __name__ == "__main__":
    main()
