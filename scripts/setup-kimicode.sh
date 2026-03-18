#!/usr/bin/env bash
# setup-kimicode.sh — Configure KimiCode adapter
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Setting up KimiCode adapter for Socialwares..."
echo ""
echo "To launch with KimiCode adapter:"
echo "  uv run agent/adapters/kimicode/launcher.py"
echo ""
echo "KimiCode SDK integration is in development."
