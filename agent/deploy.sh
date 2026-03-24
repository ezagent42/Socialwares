#!/usr/bin/env bash
# deploy.sh — Compile four primitives -> .runtime/
# Adapter-aware: generates platform-specific config (skills dir, hooks, prompt file)
#
# Usage: ./agent/deploy.sh [--adapter claude|codex|kimi]
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="$(cd "$AGENT_DIR/.." && pwd)"
RUNTIME_DIR="$APP_ROOT/.runtime"
FLOW_YAML="$AGENT_DIR/flow/flow.yaml"

# Default adapter
ADAPTER="claude"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --adapter) ADAPTER="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Root guard (prevent running at template root)
if [ -f "$APP_ROOT/scripts/create-my-socialware.py" ] && [ ! -f "$APP_ROOT/Makefile" -o "$(head -1 "$APP_ROOT/Makefile" 2>/dev/null)" = "# Socialwares Template — Root Makefile" ]; then
    echo "Error: deploy.sh should not run at the template root."
    echo ""
    echo "Create a workspace first:"
    echo "  make create ROOM=my-team APP=my-app"
    echo "  cd .socialware/workspace/my-team/my-app"
    echo "  make deploy"
    exit 1
fi

# Adapter-specific settings
case "$ADAPTER" in
    claude)
        SKILLS_SUBDIR=".claude/skills"
        HOOKS_DIR=".claude/hooks"
        PROMPT_FILE="SOUL.md"
        ;;
    codex)
        SKILLS_SUBDIR=".agents/skills"
        HOOKS_DIR=".codex/hooks"
        PROMPT_FILE="AGENTS.md"
        ;;
    kimi|kimicode)
        SKILLS_SUBDIR=".agents/skills"
        HOOKS_DIR=""  # no hooks
        PROMPT_FILE="AGENTS.md"
        ;;
    *)
        echo "Unknown adapter: $ADAPTER (supported: claude, codex, kimi)"
        exit 1
        ;;
esac

echo "Deploying four primitives (adapter: $ADAPTER)"
echo "  Source: $AGENT_DIR"
echo "  Target: $RUNTIME_DIR"
echo ""

# 1. Create .runtime/ directory structure
mkdir -p "$RUNTIME_DIR/data/Files"
mkdir -p "$RUNTIME_DIR/data/Sqlite"
mkdir -p "$RUNTIME_DIR/data/prompts"
mkdir -p "$RUNTIME_DIR/data/sessions"

# 2. Clean removed roles
if [ -d "$RUNTIME_DIR/agents" ]; then
    for old_role_dir in "$RUNTIME_DIR"/agents/*/; do
        [ -d "$old_role_dir" ] || continue
        old_role_name=$(basename "$old_role_dir")
        if [ ! -f "$AGENT_DIR/role/$old_role_name.md" ]; then
            echo "  Removing deleted role: $old_role_name"
            rm -rf "$old_role_dir"
        fi
    done
fi

# Detect python command (python3 on Unix, python on Windows)
PYTHON="python3"
command -v python3 >/dev/null 2>&1 || PYTHON="python"

# 3. Parse flow.yaml for role-action mapping (if pyyaml available)
ROLE_ACTIONS=""
if $PYTHON -c "import yaml" 2>/dev/null; then
    ROLE_ACTIONS=$($PYTHON -c "
import yaml, json
with open('$FLOW_YAML') as f:
    data = yaml.safe_load(f) or {}
result = {}
for action in data.get('direct_actions', []):
    for role in action.get('role', []):
        result.setdefault(role, []).append(action['action'])
for flow_name, flow in (data.get('flows') or {}).items():
    if isinstance(flow, dict):
        for t in flow.get('transitions', []):
            for role in t.get('role', []):
                result.setdefault(role, []).append(t['action'])
print(json.dumps(result))
" 2>/dev/null) || ROLE_ACTIONS=""
fi

# 4. Deploy each role
for role_file in "$AGENT_DIR"/role/*.md; do
    [ -f "$role_file" ] || continue
    role_name=$(basename "$role_file" .md)
    [ "$role_name" = "README" ] && continue
    role_runtime="$RUNTIME_DIR/agents/$role_name"

    mkdir -p "$role_runtime/$SKILLS_SUBDIR"

    # Write workspace root marker
    echo "$APP_ROOT" > "$role_runtime/.workspace_root"

    # Merge scope + role → prompt file
    {
        cat "$AGENT_DIR/scope/scope.md"
        echo ""
        echo "---"
        echo ""
        cat "$role_file"
    } > "$role_runtime/$PROMPT_FILE"

    # Symlink skills (filtered by flow.yaml)
    allowed_actions=""
    if [ -n "$ROLE_ACTIONS" ]; then
        allowed_actions=$(echo "$ROLE_ACTIONS" | $PYTHON -c "
import json, sys
data = json.load(sys.stdin)
for a in data.get('$role_name', []):
    print(a)
" 2>/dev/null) || allowed_actions=""
    fi

    skill_count=0
    for skill_dir in "$AGENT_DIR"/flow/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")

        if [ -n "$allowed_actions" ]; then
            echo "$allowed_actions" | grep -qx "$skill_name" || continue
        fi

        link="$role_runtime/$SKILLS_SUBDIR/$skill_name"

        [ -L "$link" ] && rm "$link"
        [ -d "$link" ] && rm -rf "$link"
        link_dir=$(dirname "$link")
        target=$($PYTHON -c "import os.path; print(os.path.relpath('$skill_dir', '$link_dir'))")
        ln -s "$target" "$link"
        skill_count=$((skill_count + 1))
    done

    # Copy commitment + flow for reference
    if [ -f "$AGENT_DIR/commitment/commitment.yaml" ]; then
        cp "$AGENT_DIR/commitment/commitment.yaml" "$role_runtime/commitment.yaml"
    fi
    cp "$FLOW_YAML" "$role_runtime/flow.yaml"

    # Generate hooks (platform-specific)
    if [ -n "$HOOKS_DIR" ]; then
        mkdir -p "$role_runtime/$HOOKS_DIR"

        # Hook script: log_prompt.sh (UserPromptSubmit)
        cat > "$role_runtime/$HOOKS_DIR/log_prompt.sh" << 'HOOKEOF'
#!/usr/bin/env bash
# UserPromptSubmit hook — record user input for commitment analysis
set -euo pipefail
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="python3"; command -v python3 >/dev/null 2>&1 || PY="python"

# Find prompts directory
if [ -f "$(cd "$SCRIPT_DIR" && pwd)/../../.workspace_root" ]; then
    WORKSPACE_ROOT=$(cat "$(cd "$SCRIPT_DIR" && pwd)/../../.workspace_root")
else
    WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi
DATA_DIR="$WORKSPACE_ROOT/.runtime/data/prompts"
mkdir -p "$DATA_DIR"

$PY -c "
import json, sys, os
from datetime import datetime, timezone
data = json.loads(sys.stdin.read())
role = os.path.basename(os.path.dirname(os.path.dirname('$SCRIPT_DIR')))
entry = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'type': 'user_prompt',
    'role': role,
    'content': data.get('prompt', ''),
    'session_id': data.get('session_id', ''),
}
log_file = os.path.join('$DATA_DIR', 'current.jsonl')
with open(log_file, 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
" <<< "$INPUT" 2>/dev/null || true
HOOKEOF
        chmod +x "$role_runtime/$HOOKS_DIR/log_prompt.sh"

        # Hook script: log_tool.sh (PreToolUse)
        cat > "$role_runtime/$HOOKS_DIR/log_tool.sh" << 'HOOKEOF'
#!/usr/bin/env bash
# PreToolUse hook — record tool calls for commitment analysis
set -euo pipefail
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="python3"; command -v python3 >/dev/null 2>&1 || PY="python"

if [ -f "$(cd "$SCRIPT_DIR" && pwd)/../../.workspace_root" ]; then
    WORKSPACE_ROOT=$(cat "$(cd "$SCRIPT_DIR" && pwd)/../../.workspace_root")
else
    WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi
DATA_DIR="$WORKSPACE_ROOT/.runtime/data/prompts"
mkdir -p "$DATA_DIR"

$PY -c "
import json, sys, os
from datetime import datetime, timezone
data = json.loads(sys.stdin.read())
role = os.path.basename(os.path.dirname(os.path.dirname('$SCRIPT_DIR')))
entry = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'type': 'tool_call',
    'role': role,
    'tool': data.get('tool_name', ''),
    'input': data.get('tool_input', {}),
    'session_id': data.get('session_id', ''),
}
log_file = os.path.join('$DATA_DIR', 'current.jsonl')
with open(log_file, 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
" <<< "$INPUT" 2>/dev/null || true
HOOKEOF
        chmod +x "$role_runtime/$HOOKS_DIR/log_tool.sh"

        # Register hooks (platform-specific format)
        case "$ADAPTER" in
            claude)
                mkdir -p "$role_runtime/.claude"
                cat > "$role_runtime/.claude/settings.local.json" << SETTINGSEOF
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$role_runtime/$HOOKS_DIR/log_prompt.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$role_runtime/$HOOKS_DIR/log_tool.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
SETTINGSEOF
                ;;
            codex)
                mkdir -p "$role_runtime/.codex"
                cat > "$role_runtime/.codex/hooks.json" << HOOKSEOF
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$role_runtime/$HOOKS_DIR/log_prompt.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$role_runtime/$HOOKS_DIR/log_tool.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
HOOKSEOF
                cat > "$role_runtime/.codex/config.toml" << CONFIGEOF
[features]
codex_hooks = true
CONFIGEOF
                ;;
        esac
    fi

    line_count=$(wc -l < "$role_runtime/$PROMPT_FILE")
    echo "  Role: $role_name"
    echo "    $PROMPT_FILE: $line_count lines"
    echo "    Skills: $skill_count"
    echo ""
done

echo "Deploy complete."
echo "  Data: $RUNTIME_DIR/data/"
echo "  Agents: $RUNTIME_DIR/agents/"
echo ""
echo "Start with: ./agent/start.sh --role <role_name> --adapter $ADAPTER"
