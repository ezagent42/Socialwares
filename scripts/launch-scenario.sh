#!/usr/bin/env bash
# launch-scenario.sh — Launch multi-agent scenario
#
# Usage:
#   ./scripts/launch-scenario.sh scenarios/examples/task-review.yaml

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <scenario.yaml>"
    echo ""
    echo "Available scenarios:"
    find "$REPO_ROOT/scenarios" -name "*.yaml" -type f 2>/dev/null | while read -r f; do
        echo "  $f"
    done
    exit 1
fi

SCENARIO="$1"

if [ ! -f "$SCENARIO" ]; then
    echo "❌ Scenario not found: $SCENARIO"
    exit 1
fi

echo "🚀 Launching multi-agent scenario..."
echo "  File: $SCENARIO"
echo ""

uv run "$REPO_ROOT/agent/adapters/claude/multi_launcher.py" "$SCENARIO"
