#!/usr/bin/env bash
# session-start.sh — Health check for Socialwares dev environment
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MSG="Socialwares dev environment active"
STATUS="ok"

if [ ! -f "${REPO_ROOT}/agent/agent.yaml" ]; then
  MSG="agent/agent.yaml missing — run ./scripts/setup-claude.sh"
  STATUS="warn"
fi

if [ ! -d "${REPO_ROOT}/.claude/skills" ]; then
  MSG=".claude/skills/ directory missing — run ./scripts/setup-claude.sh"
  STATUS="warn"
elif [ ! -L "${REPO_ROOT}/.claude/skills/taskarena" ]; then
  MSG=".claude/skills/ symlinks missing — run ./scripts/setup-claude.sh"
  STATUS="warn"
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "${MSG}"
  }
}
EOF
