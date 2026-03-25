#!/usr/bin/env python3
"""Automated conversation testing — run agent on test cases via SDK.

Sends each conversation test input to the agent via SDK,
collects traces, checks if expected skill was used, scores results.

Usage:
    uv run run_auto.py --tests-dir agent/flow/evolve_auto/conversation_tests --adapter claude
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_conversation_tests(path: Path) -> list[dict]:
    """Load conversation tests from a YAML file or directory.

    If path is a directory, reads all *.yaml files.
    If path is a file, reads that file.
    """
    cases = []
    if path.is_dir():
        for f in sorted(path.glob("*.yaml")):
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            role = data.get("role", f.stem)
            for case in data.get("cases", []):
                case["role"] = role
                cases.append(case)
    elif path.is_file():
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        role = data.get("role", "default")
        for case in data.get("cases", []):
            case["role"] = role
            cases.append(case)
    return cases


def load_adapter(adapter_name: str, project_dir: Path):
    """Load SDK adapter for the specified platform."""
    # Find adapters directory
    ws_root_file = project_dir / ".workspace_root"
    if ws_root_file.exists():
        workspace_root = Path(ws_root_file.read_text().strip())
    else:
        workspace_root = project_dir.parent.parent.parent

    adapter_path = workspace_root / "agent" / "adapters"
    sys.path.insert(0, str(adapter_path))

    actual_name = "kimicode" if adapter_name == "kimi" else adapter_name
    sys.path.insert(0, str(adapter_path / actual_name))

    from base import RoleConfig
    config = RoleConfig.from_runtime(project_dir)
    mod = importlib.import_module(f"{actual_name}.sdk")

    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if isinstance(attr, type) and hasattr(attr, "launch_sdk") and attr_name != "BaseAdapter":
            return attr(config)

    raise RuntimeError(f"No adapter found in {actual_name}/sdk.py")


async def run_single_test(adapter, case: dict) -> dict:
    """Run a single conversation test case."""
    user_input = case.get("input", "")
    expected_skill = case.get("expected_skill", "")
    description = case.get("description", user_input)

    messages = []
    print(f"    > {user_input}")
    try:
        async for message in adapter.launch_sdk(user_input):
            # Skip non-content messages (rate limits, system events)
            msg_type = getattr(message, "type", "") or ""
            if "rate_limit" in str(msg_type).lower():
                continue

            if hasattr(message, "__dict__"):
                msg_dict = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v
                            for k, v in message.__dict__.items()}
            elif isinstance(message, dict):
                msg_dict = message
            else:
                msg_dict = {"content": str(message)}
            messages.append(msg_dict)

            # Real-time stdout: print text content
            content = msg_dict.get("content", "")
            if content and isinstance(content, str) and len(content) < 500:
                print(f"    < {content[:200]}")
    except NotImplementedError:
        return {
            "description": description,
            "passed": False,
            "error": "SDK not available for this adapter",
            "messages": [],
        }
    except Exception as e:
        return {
            "description": description,
            "passed": False,
            "error": str(e),
            "messages": [],
        }

    # Check if expected skill was used
    trace_text = json.dumps(messages, default=str)
    skill_found = expected_skill.lower() in trace_text.lower() if expected_skill else True

    return {
        "description": description,
        "input": user_input,
        "expected_skill": expected_skill,
        "passed": skill_found,
        "messages": messages,
    }


async def run_all_tests(adapter, cases: list[dict]) -> list[dict]:
    """Run all conversation test cases sequentially with delay to avoid rate limits."""
    results = []
    for i, case in enumerate(cases):
        if i > 0:
            await asyncio.sleep(3)  # avoid rate limiting
        result = await run_single_test(adapter, case)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{status}] {result['description']}")
        if not result["passed"] and "error" in result:
            print(f"         Error: {result['error']}")
        results.append(result)
    return results


def main() -> None:
    # Find workspace root
    workspace_root_file = Path(".workspace_root")
    if workspace_root_file.exists():
        workspace_root = Path(workspace_root_file.read_text().strip())
        os.chdir(workspace_root)

    parser = argparse.ArgumentParser(description="Automated conversation testing")
    parser.add_argument("--tests-dir", default="agent/flow/evolve_auto/conversation_tests",
                        help="Directory with conversation test YAML files")
    parser.add_argument("--adapter", default="claude", help="Platform adapter")
    parser.add_argument("--role", default="default", help="Role to test")
    args = parser.parse_args()

    tests_path = Path(args.tests_dir)
    cases = load_conversation_tests(tests_path)

    if not cases:
        print("No conversation tests found.")
        sys.exit(0)

    # Find project dir
    runtime_dir = Path(".runtime")
    project_dir = runtime_dir / "agents" / args.role
    if not project_dir.exists():
        print(f"Error: Role '{args.role}' not found at {project_dir}")
        sys.exit(1)

    adapter = load_adapter(args.adapter, project_dir)

    print(f"Running {len(cases)} conversation tests (role: {args.role}, adapter: {args.adapter})")
    print()

    results = asyncio.run(run_all_tests(adapter, cases))

    # List failures (no suggestions — evolver LLM analyzes these)
    failures = [r for r in results if not r["passed"]]
    if failures:
        print()
        print("Failures:")
        for f in failures:
            print(f"  [{f.get('expected_skill', '?')}] Input: \"{f.get('input', '')}\"")
            if "error" in f:
                print(f"    Error: {f['error']}")
            else:
                print(f"    Expected skill '{f.get('expected_skill', '')}' not found in trace")

    # Score
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    score = passed / total if total > 0 else 0

    print()
    print(f"Conversation Score: {passed}/{total} ({score:.0%})")

    # Save report
    report_dir = Path(".runtime/data/evolve/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"auto_test_{timestamp}.json"

    report_data = {
        "type": "auto_test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": str(args.tests_dir),
        "score": score,
        "passed": passed,
        "total": total,
        "summary": f"Conversation Score: {passed}/{total} ({score:.0%})",
        "details": results,
        "failures": [{"input": f.get("input"), "expected_skill": f.get("expected_skill"), "error": f.get("error")} for f in failures],
        "note": "Improvement suggestions are made by evolver (LLM), not this script.",
    }
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

    # Save auto-generated sessions to isolated directory
    sessions_dir = Path(".runtime/data/evolve/auto_sessions")
    sessions_dir.mkdir(parents=True, exist_ok=True)
    sessions_file = sessions_dir / f"session_{timestamp}.json"
    with open(sessions_file, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": args.role,
            "adapter": args.adapter,
            "conversations": results,
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"Report saved to {report_file}")


if __name__ == "__main__":
    main()
