#!/usr/bin/env python3
"""Diagnose — extract commitment-related events from conversation data.

Reads hook logs (prompts/*.jsonl) and SDK sessions (sessions/*.json),
extracts events matching commitment actions, outputs structured data
for evolver (LLM) to analyze conditions and judge fulfillment.

The script does NOT judge fulfillment — conditions are natural language,
only the evolver (LLM) can interpret them.

Usage:
    uv run diagnose.py --data-dir .runtime/data --commitment agent/commitment/commitment.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
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
    state_dir = data_dir / "evolve"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "state.yaml"
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


def extract_commitment_events(
    commitments: dict,
    prompt_entries: list[dict],
    sessions: list[dict],
) -> dict:
    """Extract events matching each commitment's from/to actions.

    Returns raw event data per commitment — does NOT judge fulfillment.
    The evolver (LLM) reads this data + conditions to judge.
    """
    results = {}

    for cid, c in commitments.items():
        from_action = c.get("from", {}).get("action", "")
        from_role = c.get("from", {}).get("role", "")
        to_action = c.get("to", {}).get("action", "")
        to_role = c.get("to", {}).get("role", "")
        condition = c.get("condition", "")

        from_events = []
        to_events = []

        for entry in prompt_entries:
            tool = entry.get("tool", "")
            tool_input = entry.get("input", {})
            timestamp = entry.get("timestamp", "")
            role = entry.get("role", "")

            # Match Skill tool calls by exact action name
            skill_name = ""
            if tool == "Skill" and isinstance(tool_input, dict):
                skill_name = tool_input.get("skill", "")

            # Also check Bash commands for API endpoint patterns
            bash_cmd = ""
            if tool == "Bash" and isinstance(tool_input, dict):
                bash_cmd = tool_input.get("command", "")

            if from_action and (skill_name == from_action or from_action in bash_cmd):
                from_events.append({"timestamp": timestamp, "role": role, "tool": tool, "detail": skill_name or bash_cmd})
            if to_action and (skill_name == to_action or to_action in bash_cmd):
                to_events.append({"timestamp": timestamp, "role": role, "tool": tool, "detail": skill_name or bash_cmd})

        # Also check SDK sessions
        for session in sessions:
            for msg in session.get("messages", []):
                msg_text = json.dumps(msg)
                ts = msg.get("timestamp", session.get("started_at", ""))
                if from_action and from_action in msg_text:
                    from_events.append({"timestamp": ts, "role": session.get("role", ""), "tool": "sdk", "detail": msg_text[:200]})
                if to_action and to_action in msg_text:
                    to_events.append({"timestamp": ts, "role": session.get("role", ""), "tool": "sdk", "detail": msg_text[:200]})

        results[cid] = {
            "from": {"role": from_role, "action": from_action},
            "to": {"role": to_role, "action": to_action},
            "condition": condition,
            "on_violation": c.get("on_violation"),
            "from_events": from_events,
            "to_events": to_events,
        }

    return results


def generate_report(
    commitments: dict,
    extracted: dict,
    prompt_count: int,
    session_count: int,
) -> str:
    """Generate extraction report (facts only, no judgment)."""
    lines = []
    lines.append("=" * 60)
    lines.append("DIAGNOSTIC DATA EXTRACTION")
    lines.append("=" * 60)
    lines.append("")

    lines.append("## Data Sources")
    lines.append(f"  Hook log entries: {prompt_count}")
    lines.append(f"  SDK sessions: {session_count}")
    lines.append("")

    lines.append("## Commitment Events")
    if not extracted:
        lines.append("  No commitments defined.")
    else:
        for cid, data in extracted.items():
            lines.append(f"  [{cid}] {data['from']['action']} → {data['to']['action']}")
            lines.append(f"         condition: {data['condition']}")
            lines.append(f"         from events: {len(data['from_events'])}")
            for evt in data["from_events"]:
                lines.append(f"           {evt['timestamp']} [{evt['role']}] {evt['detail']}")
            lines.append(f"         to events: {len(data['to_events'])}")
            for evt in data["to_events"]:
                lines.append(f"           {evt['timestamp']} [{evt['role']}] {evt['detail']}")
            lines.append("")

    lines.append("NOTE: Fulfillment judgment is NOT made by this script.")
    lines.append("The evolver (LLM) reads this data + commitment conditions to judge.")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def main() -> None:
    # Find workspace root
    workspace_root_file = Path(".workspace_root")
    if workspace_root_file.exists():
        workspace_root = Path(workspace_root_file.read_text().strip())
        os.chdir(workspace_root)

    parser = argparse.ArgumentParser(description="Extract commitment events from conversation data")
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

    # Extract events (no judgment)
    extracted = extract_commitment_events(commitments, prompt_entries, sessions)

    # Print text report
    report = generate_report(commitments, extracted, len(prompt_entries), len(sessions))
    print(report)

    # Save structured JSON (for evolver to read and judge)
    report_dir = data_dir / "evolve" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    report_file = report_dir / f"diagnose_{timestamp_str}.json"

    report_data = {
        "type": "diagnose",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "prompts/*.jsonl + sessions/*.json",
        "prompt_count": len(prompt_entries),
        "session_count": len(sessions),
        "commitments": extracted,
        "note": "Fulfillment NOT judged. Evolver reads this + conditions to judge.",
    }
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"Report saved to {report_file}")

    # Update cursor
    new_cursor = {
        "last_extraction": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompts_line": cursor.get("prompts_line", 0) + len(prompt_entries),
            "sessions_cursor": sorted(
                (data_dir / "sessions").glob("*.json")
            )[-1].name if (data_dir / "sessions").exists() and list((data_dir / "sessions").glob("*.json")) else "",
        },
    }
    save_cursor(data_dir, new_cursor)


if __name__ == "__main__":
    main()
