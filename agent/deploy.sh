#!/usr/bin/env bash
# deploy.sh — Compile four primitives -> .runtime/
#
# Idempotent: safe to run multiple times. Detects added/removed roles and skills.
# Reads agent/ from the SAME directory as this script (workspace-local).
# Reads flow.yaml to determine which actions each role can access.
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

# 2. Clean up removed roles — delete .runtime/agents/{role}/ if agent/role/{role}/ no longer exists
if [ -d "$RUNTIME_DIR/agents" ]; then
    for old_role_dir in "$RUNTIME_DIR"/agents/*/; do
        [ -d "$old_role_dir" ] || continue
        old_role_name=$(basename "$old_role_dir")
        if [ ! -d "$AGENT_DIR/role/$old_role_name" ]; then
            echo "  Removing deleted role: $old_role_name"
            rm -rf "$old_role_dir"
        fi
    done
fi

# 3. Parse flow.yaml to build role→actions mapping
get_actions_for_role() {
    local role_name="$1"
    if [ ! -f "$FLOW_YAML" ]; then
        # No flow.yaml — all actions for all roles
        for d in "$AGENT_DIR"/flow/*/; do
            [ -d "$d" ] && basename "$d"
        done
        return
    fi

    python3 - "$FLOW_YAML" "$role_name" << 'PYEOF'
import sys
try:
    import yaml
except ImportError:
    # pyyaml not installed — fallback to all actions
    import os
    flow_dir = os.path.dirname(sys.argv[1])
    for d in os.listdir(flow_dir):
        if os.path.isdir(os.path.join(flow_dir, d)):
            print(d)
    sys.exit(0)

flow_yaml = sys.argv[1]
role_name = sys.argv[2]

with open(flow_yaml) as f:
    data = yaml.safe_load(f) or {}

actions = set()

for flow_id, flow_def in (data.get("flows") or {}).items():
    if not isinstance(flow_def, dict):
        continue
    for t in flow_def.get("transitions", []):
        roles = t.get("role", [])
        if isinstance(roles, str):
            roles = [roles]
        if "any" in roles or role_name in roles:
            actions.add(t["action"])

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

# 4. Generate an isolated PROJECT_DIR for each role
for role_dir in "$AGENT_DIR"/role/*/; do
    [ -d "$role_dir" ] || continue
    role_name=$(basename "$role_dir")
    role_runtime="$RUNTIME_DIR/agents/$role_name"

    echo "  Role: $role_name"

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

    # Clear old skills (clean slate for idempotent rebuild)
    rm -rf "$role_runtime/.claude/skills/"*

    # Symlink allowed skills from flow/ (relative paths for portability)
    skill_count=0
    for skill_dir in "$AGENT_DIR"/flow/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")

        if [ -n "$allowed_actions" ]; then
            echo "$allowed_actions" | grep -qx "$skill_name" || continue
        fi

        link="$role_runtime/.claude/skills/$skill_name"
        link_dir=$(dirname "$link")
        target=$(python3 -c "import os.path; print(os.path.relpath('$skill_dir', '$link_dir'))")

        ln -s "$target" "$link"
        skill_count=$((skill_count + 1))
    done

    # Generate PostToolUse conversation logging hook
    cat > "$role_runtime/.claude/hooks/log_action.sh" << 'HOOKEOF'
#!/usr/bin/env bash
# PostToolUse hook — log tool calls to .runtime/data/conversations/
set -euo pipefail
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Navigate from .claude/hooks/ up to .runtime/
RUNTIME_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA_DIR="$(cd "$RUNTIME_DIR/../.." && pwd)/data/conversations"
mkdir -p "$DATA_DIR"

TIMESTAMP=$(python3 -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())")
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name','unknown'))" 2>/dev/null || echo "unknown")

python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
entry = {
    'timestamp': '$TIMESTAMP',
    'role': '$(basename \"$RUNTIME_DIR\")',
    'type': 'tool_call',
    'tool': data.get('tool_name', 'unknown'),
    'input': data.get('tool_input', {}),
}
with open('$DATA_DIR/current.jsonl', 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
" <<< "$INPUT" 2>/dev/null || true
HOOKEOF
    chmod +x "$role_runtime/.claude/hooks/log_action.sh"

    # Copy commitment constraints configuration
    if [ -f "$AGENT_DIR/commitment/constraints.yaml" ]; then
        cp "$AGENT_DIR/commitment/constraints.yaml" "$role_runtime/constraints.yaml"
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
