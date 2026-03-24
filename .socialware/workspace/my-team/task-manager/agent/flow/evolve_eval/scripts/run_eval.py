#!/usr/bin/env python3
"""Run eval cases against a live Socialware App.

Reads eval_cases.yaml, makes HTTP requests, compares responses.
Outputs pass/fail per case and overall score.

Usage:
    uv run run_eval.py --cases eval_cases.yaml --base-url http://localhost:8001
    uv run run_eval.py --cases eval_cases.yaml  # default: http://localhost:8001
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml


def load_cases(path: Path) -> tuple[list[dict], list[dict]]:
    """Load eval cases from YAML file.

    Returns (api_checks, conversation_checks).
    """
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    api_checks = data.get("api_checks", [])
    conversation_checks = data.get("conversation_checks", [])

    # Backward compatible: old format with just "cases"
    if "cases" in data and not api_checks:
        api_checks = data["cases"]

    return api_checks, conversation_checks


def run_case(case: dict, base_url: str) -> dict:
    """Run a single eval case. Returns result dict."""
    method = case.get("method", "GET").upper()
    endpoint = case.get("endpoint", "/")
    url = f"{base_url}{endpoint}"
    headers = case.get("headers", {})
    headers.setdefault("Content-Type", "application/json")
    body = case.get("body")
    if isinstance(body, str):
        body = body.encode()
    elif isinstance(body, dict):
        body = json.dumps(body).encode()

    try:
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=10) as resp:
            status = resp.status
            resp_body = resp.read().decode()
    except HTTPError as e:
        status = e.code
        resp_body = e.read().decode()
    except URLError as e:
        return {
            "description": case.get("description", endpoint),
            "passed": False,
            "error": f"Connection failed: {e.reason}",
        }
    except Exception as e:
        return {
            "description": case.get("description", endpoint),
            "passed": False,
            "error": str(e),
        }

    # Check status
    expected_status = case.get("expected_status", 200)
    status_ok = status == expected_status

    # Check body (if specified)
    body_ok = True
    if "expected_body" in case:
        try:
            actual = json.loads(resp_body)
            expected = json.loads(case["expected_body"])
            body_ok = actual == expected
        except (json.JSONDecodeError, TypeError):
            body_ok = resp_body.strip() == case["expected_body"].strip()

    passed = status_ok and body_ok

    result = {
        "description": case.get("description", endpoint),
        "passed": passed,
        "status": status,
        "expected_status": expected_status,
    }
    if not status_ok:
        result["status_mismatch"] = f"got {status}, expected {expected_status}"
    if not body_ok:
        result["body_mismatch"] = f"response did not match expected"

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run eval cases against Socialware App")
    parser.add_argument("--cases", required=True, help="Path to eval_cases.yaml")
    parser.add_argument("--base-url", default="http://localhost:8001", help="App base URL")
    args = parser.parse_args()

    api_checks, conversation_checks = load_cases(Path(args.cases))

    if not api_checks and not conversation_checks:
        print("No eval cases found.")
        sys.exit(0)

    # Run API checks
    results = []
    api_score = 0
    if api_checks:
        print(f"Running {len(api_checks)} API checks against {args.base_url}")
        print()
        for case in api_checks:
            result = run_case(case, args.base_url)
            results.append(result)
            status = "PASS" if result["passed"] else "FAIL"
            print(f"  [{status}] {result['description']}")
            if not result["passed"]:
                for key in ["status_mismatch", "body_mismatch", "error"]:
                    if key in result:
                        print(f"         {result[key]}")

        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        api_score = passed / total if total > 0 else 0
        print(f"\nAPI Score: {passed}/{total} ({api_score:.0%})")

    # Report conversation checks (require agent runtime)
    if conversation_checks:
        print(f"\nConversation checks ({len(conversation_checks)} defined):")
        for cc in conversation_checks:
            print(f"  [ ] {cc.get('input', '?')} → expects: {cc.get('expected_skill', '?')}")
        print("  (Run these interactively with evolver role)")

    # Save results for evolver to read
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    score = passed / total if total > 0 else 0
    results_file = Path(args.cases).parent / "last_eval_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "score": score,
            "passed": passed,
            "total": total,
            "results": results,
            "conversation_checks_count": len(conversation_checks),
        }, f, indent=2)
    print(f"Results saved to {results_file}")


if __name__ == "__main__":
    main()
