#!/usr/bin/env python3
"""Multi-agent scenario launcher for Claude SDK.

Reads a scenario YAML and launches multiple agents.

Usage:
  uv run multi_launcher.py ../../scenarios/examples/task-review.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import AgentConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch multi-agent scenario")
    parser.add_argument("scenario", help="Path to scenario YAML")
    args = parser.parse_args()

    with open(args.scenario) as f:
        scenario = yaml.safe_load(f)

    print(f"[Multi-Launcher] Scenario: {scenario['name']}")
    print(f"[Multi-Launcher] Description: {scenario.get('description', '')}")
    print()

    for agent_cfg in scenario.get("agents", []):
        template_dir = Path(args.scenario).parent.parent.parent / agent_cfg["template"]
        print(f"[Multi-Launcher] Agent: {agent_cfg['name']}")
        print(f"  Template: {agent_cfg['template']}")
        print(f"  Adapter: {agent_cfg.get('adapter', 'claude')}")
        print(f"  Roles: {agent_cfg.get('roles', [])}")
        print(f"  Template exists: {template_dir.exists()}")
        print()

    # TODO: Actually launch agents with asyncio
    print("[Multi-Launcher] Mock mode — would launch all agents concurrently via bus")


if __name__ == "__main__":
    main()
