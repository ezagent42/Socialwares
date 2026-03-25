#!/usr/bin/env python3
"""Check structural consistency of four primitives.

Verifies that all cross-references between role, scope, commitment, and flow
are valid. Does not require the app to be running.

Usage:
    uv run check_structure.py --agent-dir agent
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def check_flow_skills(agent_dir: Path) -> list[str]:
    """Check that every action in flow.yaml has a SKILL.md."""
    flow_yaml = agent_dir / "flow" / "flow.yaml"
    if not flow_yaml.exists():
        return ["flow.yaml not found"]

    with open(flow_yaml) as f:
        data = yaml.safe_load(f) or {}

    issues = []
    actions = set()

    for action in data.get("direct_actions", []):
        name = action.get("action", "")
        actions.add(name)
        skill_dir = agent_dir / "flow" / name
        if not skill_dir.exists():
            issues.append(f"MISSING SKILL: action '{name}' has no directory agent/flow/{name}/")
        elif not (skill_dir / "SKILL.md").exists():
            issues.append(f"MISSING SKILL.md: agent/flow/{name}/ exists but has no SKILL.md")

    for flow_name, flow in (data.get("flows") or {}).items():
        if isinstance(flow, dict):
            for t in flow.get("transitions", []):
                name = t.get("action", "")
                actions.add(name)
                skill_dir = agent_dir / "flow" / name
                if not skill_dir.exists():
                    issues.append(f"MISSING SKILL: transition action '{name}' (flow {flow_name}) has no directory")

    return issues


def check_commitment_refs(agent_dir: Path) -> list[str]:
    """Check that commitment references valid roles and actions."""
    commitment_file = agent_dir / "commitment" / "commitment.yaml"
    if not commitment_file.exists():
        return []  # No commitments defined — not an error

    with open(commitment_file) as f:
        data = yaml.safe_load(f) or {}

    commitments = data.get("commitments", {})
    if not commitments:
        return []

    # Collect existing roles
    existing_roles = set()
    role_dir = agent_dir / "role"
    if role_dir.exists():
        for f in role_dir.iterdir():
            if f.is_file() and f.suffix == ".md" and f.name != "README.md":
                existing_roles.add(f.stem)

    # Collect existing actions from flow.yaml
    existing_actions = set()
    flow_yaml = agent_dir / "flow" / "flow.yaml"
    if flow_yaml.exists():
        with open(flow_yaml) as f:
            flow_data = yaml.safe_load(f) or {}
        for action in flow_data.get("direct_actions", []):
            existing_actions.add(action.get("action", ""))
        for flow_name, flow in (flow_data.get("flows") or {}).items():
            if isinstance(flow, dict):
                for t in flow.get("transitions", []):
                    existing_actions.add(t.get("action", ""))

    issues = []
    for cid, c in commitments.items():
        # Check from
        from_spec = c.get("from", {})
        from_role = from_spec.get("role", "")
        from_action = from_spec.get("action", "")
        if from_role and from_role not in existing_roles:
            issues.append(f"COMMITMENT {cid}: from.role '{from_role}' not found in role/")
        if from_action and from_action not in existing_actions:
            issues.append(f"COMMITMENT {cid}: from.action '{from_action}' not found in flow.yaml")

        # Check to
        to_spec = c.get("to", {})
        to_role = to_spec.get("role", "")
        to_action = to_spec.get("action", "")
        if to_role and to_role not in existing_roles:
            issues.append(f"COMMITMENT {cid}: to.role '{to_role}' not found in role/")
        if to_action and to_action not in existing_actions:
            issues.append(f"COMMITMENT {cid}: to.action '{to_action}' not found in flow.yaml")

        # Check on_violation
        violation = c.get("on_violation")
        if violation:
            v_role = violation.get("role", "")
            v_action = violation.get("action", "")
            if v_role and v_role not in existing_roles:
                issues.append(f"COMMITMENT {cid}: on_violation.role '{v_role}' not found in role/")
            if v_action and v_action not in existing_actions:
                issues.append(f"COMMITMENT {cid}: on_violation.action '{v_action}' not found in flow.yaml")

    return issues


def check_scope(agent_dir: Path) -> list[str]:
    """List scope capabilities for manual review."""
    scope_file = agent_dir / "scope" / "scope.md"
    if not scope_file.exists():
        return ["scope.md not found"]

    content = scope_file.read_text()
    info = []
    in_capabilities = False
    for line in content.splitlines():
        if "## Capabilities" in line or "## capabilities" in line:
            in_capabilities = True
            continue
        if in_capabilities:
            if line.startswith("##"):
                break
            if line.strip().startswith("-"):
                info.append(f"  SCOPE: {line.strip()}")

    if not info:
        info.append("  SCOPE: No capabilities section found in scope.md")

    return info


def main() -> None:
    # Find workspace root
    workspace_root_file = Path(".workspace_root")
    if workspace_root_file.exists():
        workspace_root = Path(workspace_root_file.read_text().strip())
        os.chdir(workspace_root)

    parser = argparse.ArgumentParser(description="Check four primitives structural consistency")
    parser.add_argument("--agent-dir", default="agent", help="Agent directory")
    args = parser.parse_args()

    agent_dir = Path(args.agent_dir)
    if not agent_dir.exists():
        print(f"Error: {agent_dir} not found")
        sys.exit(1)

    print("=" * 60)
    print("STRUCTURE CHECK REPORT")
    print("=" * 60)
    print()

    # 1. Flow → SKILL.md
    print("## Flow Actions → SKILL.md")
    flow_issues = check_flow_skills(agent_dir)
    if flow_issues:
        for issue in flow_issues:
            print(f"  ✗ {issue}")
    else:
        print("  ✓ All actions have SKILL.md")
    print()

    # 2. Commitment references
    print("## Commitment References")
    commit_issues = check_commitment_refs(agent_dir)
    if commit_issues:
        for issue in commit_issues:
            print(f"  ✗ {issue}")
    else:
        print("  ✓ All commitment references valid (or no commitments defined)")
    print()

    # 3. Scope capabilities
    print("## Scope Capabilities (for manual review)")
    scope_info = check_scope(agent_dir)
    for info in scope_info:
        print(info)
    print()

    # Summary
    total_issues = len(flow_issues) + len(commit_issues)
    print("=" * 60)
    if total_issues == 0:
        print(f"PASS: No structural issues found.")
    else:
        print(f"ISSUES: {total_issues} problem(s) found.")
    print("=" * 60)

    # Save report
    report_dir = Path(".runtime/data/evolve/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    report_file = report_dir / f"check_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"

    report_data = {
        "type": "check",
        "timestamp": timestamp.isoformat(),
        "source": str(agent_dir),
        "score": 1.0 if total_issues == 0 else max(0, 1.0 - total_issues * 0.1),
        "passed": (len(flow_issues) == 0) + (len(commit_issues) == 0),
        "total": 2,
        "summary": "All structure checks passed" if total_issues == 0 else f"{total_issues} issues found",
        "details": flow_issues + commit_issues,
        "suggestions": [
            {"primitive": "flow", "action": f"Create SKILL.md for: {issue.split(chr(39))[1]}", "reason": issue}
            for issue in flow_issues if "MISSING" in issue
        ] + [
            {"primitive": "commitment" if "commitment" in issue.lower() else "role",
             "action": "Add missing reference", "reason": issue}
            for issue in commit_issues
        ],
    }

    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"Report saved to {report_file}")

    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()
