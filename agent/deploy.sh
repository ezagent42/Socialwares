#!/usr/bin/env bash
# deploy.sh — Compile four primitives -> .runtime/
#
# Reads agent/ from the SAME directory as this script (workspace-local).
# Generates an isolated $PROJECT_DIR for each role.
#
# Usage (from within a workspace):
#   ./agent/deploy.sh
#
# Or from repo root for the template:
#   ./agent/deploy.sh
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="$(cd "$AGENT_DIR/.." && pwd)"
RUNTIME_DIR="$APP_ROOT/.runtime"

echo "Deploying four primitives"
echo "  Source: $AGENT_DIR"
echo "  Target: $RUNTIME_DIR"
echo ""

# 1. Create .runtime/ directory structure
mkdir -p "$RUNTIME_DIR/data/Files"
mkdir -p "$RUNTIME_DIR/data/Sqlite"

# 2. Generate an isolated PROJECT_DIR for each role
for role_dir in "$AGENT_DIR"/role/*/; do
    [ -d "$role_dir" ] || continue
    role_name=$(basename "$role_dir")
    role_runtime="$RUNTIME_DIR/agents/$role_name"

    echo "  Role: $role_name"

    # Create directories
    mkdir -p "$role_runtime/.claude/skills"
    mkdir -p "$role_runtime/.claude/hooks"

    # Merge SOUL.md: scope/SOUL.md + role/{name}/SOUL.md
    {
        cat "$AGENT_DIR/scope/SOUL.md" 2>/dev/null || true
        echo ""
        echo "---"
        echo ""
        cat "$role_dir/SOUL.md" 2>/dev/null || true
    } > "$role_runtime/SOUL.md"

    # Symlink each skill from flow/ (relative paths for portability)
    for skill_dir in "$AGENT_DIR"/flow/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")
        link="$role_runtime/.claude/skills/$skill_name"

        link_dir=$(dirname "$link")
        target=$(python3 -c "import os.path; print(os.path.relpath('$skill_dir', '$link_dir'))")

        [ -L "$link" ] && rm "$link"
        [ -d "$link" ] && rm -rf "$link"

        ln -s "$target" "$link"
    done

    # Copy commitment eval configuration
    if [ -f "$AGENT_DIR/commitment/eval.yaml" ]; then
        cp "$AGENT_DIR/commitment/eval.yaml" "$role_runtime/eval.yaml"
    fi

    echo "    SOUL.md: $(wc -l < "$role_runtime/SOUL.md") lines"
    echo "    Skills: $(ls "$role_runtime/.claude/skills/" 2>/dev/null | wc -l)"
    echo ""
done

echo "Deploy complete."
echo "  Data: $RUNTIME_DIR/data/"
echo "  Agents: $RUNTIME_DIR/agents/"
echo ""
echo "Start with: ./agent/start.sh --role <role_name>"
