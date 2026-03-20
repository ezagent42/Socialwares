#!/usr/bin/env bash
# deploy.sh — Compile four primitives -> .runtime/
#
# Reads agent/ from the SAME directory as this script (workspace-local).
# Reads flow.yaml to determine which actions each role can access.
# Generates an isolated $PROJECT_DIR for each role.
#
# Usage (from within a workspace or repo root):
#   ./agent/deploy.sh
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="$(cd "$AGENT_DIR/.." && pwd)"
RUNTIME_DIR="$APP_ROOT/.runtime"
FLOW_YAML="$AGENT_DIR/flow/flow.yaml"

echo "Deploying four primitives"
echo "  Source: $AGENT_DIR"
echo "  Target: $RUNTIME_DIR"
echo ""

# 1. Create .runtime/ directory structure
mkdir -p "$RUNTIME_DIR/data/Files"
mkdir -p "$RUNTIME_DIR/data/Sqlite"

# 2. Parse flow.yaml to build role→actions mapping
# If flow.yaml exists, only symlink actions allowed for each role.
# If no flow.yaml, symlink all actions for all roles (backward compatible).
get_actions_for_role() {
    local role_name="$1"
    if [ ! -f "$FLOW_YAML" ]; then
        # No flow.yaml — all actions for all roles
        for d in "$AGENT_DIR"/flow/*/; do
            [ -d "$d" ] && basename "$d"
        done
        return
    fi

    # Parse flow.yaml with Python for reliable YAML handling
    python3 - "$FLOW_YAML" "$role_name" << 'PYEOF'
import sys, yaml
from pathlib import Path

flow_yaml = sys.argv[1]
role_name = sys.argv[2]

with open(flow_yaml) as f:
    data = yaml.safe_load(f) or {}

actions = set()

# Collect actions from state machine flows
for flow_id, flow_def in (data.get("flows") or {}).items():
    if not isinstance(flow_def, dict):
        continue
    for t in flow_def.get("transitions", []):
        roles = t.get("role", [])
        if isinstance(roles, str):
            roles = [roles]
        if "any" in roles or role_name in roles:
            actions.add(t["action"])

# Collect direct actions
for da in data.get("direct_actions", []):
    roles = da.get("role", [])
    if isinstance(roles, str):
        roles = [roles]
    if "any" in roles or role_name in roles:
        actions.add(da["action"])

for a in sorted(actions):
    print(a)
PYEOF
}

# 3. Generate an isolated PROJECT_DIR for each role
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

    # Get allowed actions for this role
    allowed_actions=$(get_actions_for_role "$role_name")

    # Clear old skills
    rm -rf "$role_runtime/.claude/skills/"*

    # Symlink allowed skills from flow/ (relative paths for portability)
    skill_count=0
    for skill_dir in "$AGENT_DIR"/flow/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")

        # Check if this action is allowed for this role
        if [ -n "$allowed_actions" ]; then
            echo "$allowed_actions" | grep -qx "$skill_name" || continue
        fi

        link="$role_runtime/.claude/skills/$skill_name"
        link_dir=$(dirname "$link")
        target=$(python3 -c "import os.path; print(os.path.relpath('$skill_dir', '$link_dir'))")

        ln -s "$target" "$link"
        skill_count=$((skill_count + 1))
    done

    # Copy commitment eval configuration
    if [ -f "$AGENT_DIR/commitment/eval.yaml" ]; then
        cp "$AGENT_DIR/commitment/eval.yaml" "$role_runtime/eval.yaml"
    fi

    # Copy flow.yaml for reference
    if [ -f "$FLOW_YAML" ]; then
        cp "$FLOW_YAML" "$role_runtime/flow.yaml"
    fi

    echo "    SOUL.md: $(wc -l < "$role_runtime/SOUL.md") lines"
    echo "    Skills: $skill_count"
    echo ""
done

echo "Deploy complete."
echo "  Data: $RUNTIME_DIR/data/"
echo "  Agents: $RUNTIME_DIR/agents/"
echo ""
echo "Start with: ./agent/start.sh --role <role_name>"
