#!/usr/bin/env python3
"""Automated evolution loop for Socialware agent configuration.

Runs an evaluate → diagnose → propose → apply → re-evaluate loop.
Can optionally use EvoSkill library for more sophisticated evolution.

Usage:
    uv run run_loop.py --eval-cases eval_cases.yaml --base-url http://localhost:8001 --iterations 5
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_eval(eval_cases: Path, base_url: str) -> dict:
    """Run eval cases and return results."""
    eval_script = Path("agent/flow/evolve_eval/scripts/run_eval.py")

    result = subprocess.run(
        [sys.executable, str(eval_script), "--cases", str(eval_cases), "--base-url", base_url],
        capture_output=True, text=True,
    )

    # Parse results from saved file
    results_file = eval_cases.parent / "last_eval_results.json"
    if results_file.exists():
        with open(results_file) as f:
            return json.load(f)
    return {"score": 0, "passed": 0, "total": 0, "results": []}


def run_diagnose(data_dir: Path, constraints: Path) -> str:
    """Run diagnostic and return report."""
    diag_script = Path("agent/flow/evolve_diagnose/scripts/diagnose.py")

    result = subprocess.run(
        [sys.executable, str(diag_script), "--data-dir", str(data_dir), "--constraints", str(constraints)],
        capture_output=True, text=True,
    )
    return result.stdout


def get_failures(eval_results: dict) -> list[dict]:
    """Extract failed cases from eval results."""
    return [r for r in eval_results.get("results", []) if not r.get("passed")]


def main() -> None:
    # Find workspace root
    workspace_root_file = Path(".workspace_root")
    if workspace_root_file.exists():
        workspace_root = Path(workspace_root_file.read_text().strip())
        os.chdir(workspace_root)

    parser = argparse.ArgumentParser(description="Automated evolution loop")
    parser.add_argument("--eval-cases", required=True, help="Path to eval_cases.yaml")
    parser.add_argument("--base-url", default="http://localhost:8001", help="App base URL")
    parser.add_argument("--iterations", type=int, default=5, help="Max iterations")
    parser.add_argument("--agent-dir", default="agent", help="Agent directory")
    args = parser.parse_args()

    eval_cases = Path(args.eval_cases)
    agent_dir = Path(args.agent_dir)
    data_dir = Path(".runtime/data")
    constraints = agent_dir / "commitment" / "commitment.yaml"

    print(f"Automated Evolution Loop")
    print(f"  Eval cases: {eval_cases}")
    print(f"  Base URL: {args.base_url}")
    print(f"  Max iterations: {args.iterations}")
    print()

    # Backup agent/ before starting
    backup_dir = Path(".runtime/evolve_backup")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(agent_dir, backup_dir, ignore=shutil.ignore_patterns("adapters", "deploy.sh", "start.sh"))
    print(f"  Backup saved to {backup_dir}")
    print()

    # Initial eval
    print("=== Initial Evaluation ===")
    initial = run_eval(eval_cases, args.base_url)
    initial_score = initial.get("score", 0)
    print(f"  Initial score: {initial_score:.0%}")
    print()

    best_score = initial_score
    changes_made = []

    for i in range(1, args.iterations + 1):
        print(f"=== Iteration {i}/{args.iterations} ===")

        # Get failures
        failures = get_failures(initial if i == 1 else run_eval(eval_cases, args.base_url))
        if not failures:
            print("  No failures — nothing to improve.")
            break

        print(f"  Failures: {len(failures)}")
        for f in failures[:3]:
            print(f"    - {f.get('description', 'unknown')}")

        # Run diagnosis
        diagnosis = run_diagnose(data_dir, constraints)

        # At this point, in a full EvoSkill integration, the proposer would:
        # 1. Analyze failures + diagnosis
        # 2. Propose a specific skill or SOUL.md change
        # 3. Generator would create the change
        # 4. We'd re-evaluate
        #
        # For now, we report what was found and let the developer decide.
        print()
        print(f"  Diagnosis available at .runtime/data/last_diagnosis.txt")
        print(f"  To apply improvements manually, use: evolve_improve")
        print()

        # NOTE: Full EvoSkill integration would go here:
        # try:
        #     from evoskill import SelfImprovingLoop
        #     loop = SelfImprovingLoop(...)
        #     result = loop.run_single_iteration(failures, diagnosis)
        #     ...
        # except ImportError:
        #     print("  EvoSkill not installed. Using manual mode.")

        changes_made.append({"iteration": i, "failures": len(failures)})

    # Final eval
    print("=== Final Evaluation ===")
    final = run_eval(eval_cases, args.base_url)
    final_score = final.get("score", 0)
    print(f"  Score: {initial_score:.0%} → {final_score:.0%}")
    print()

    # Summary
    print("=== Summary ===")
    print(f"  Iterations: {len(changes_made)}")
    print(f"  Score: {initial_score:.0%} → {final_score:.0%}")
    print(f"  Backup: {backup_dir}")
    print()

    if final_score > initial_score:
        print("  Score improved. Changes are in agent/.")
        print("  Run ./agent/deploy.sh to apply.")
    elif final_score == initial_score:
        print("  No score change. Review diagnosis for manual improvements.")
    else:
        print(f"  Score decreased. Restore backup:")
        print(f"    rm -rf agent/role agent/scope agent/commitment agent/flow")
        print(f"    cp -r {backup_dir}/* agent/")

    # Save loop results
    results_file = data_dir / "last_evolve_loop.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "w") as f:
        json.dump({
            "initial_score": initial_score,
            "final_score": final_score,
            "iterations": len(changes_made),
            "changes": changes_made,
        }, f, indent=2)
    print(f"\n  Results saved to {results_file}")


if __name__ == "__main__":
    main()
