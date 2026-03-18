#!/usr/bin/env bash
# setup-codex.sh — Configure OpenAI Codex adapter
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Setting up Codex adapter for Socialwares..."
echo ""

# Check if gitagent CLI is available
if command -v gitagent &> /dev/null; then
    echo "gitagent found, exporting..."
    cd "$REPO_ROOT/agent"
    gitagent export --format openai
    echo "✓ Exported to OpenAI format"
else
    echo "gitagent CLI not found. Using manual adapter."
    echo ""
    echo "To launch with Codex adapter:"
    echo "  uv run agent/adapters/codex/launcher.py"
    echo ""
    echo "To install gitagent:"
    echo "  npm install -g gitagent"
fi
