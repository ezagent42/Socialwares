#!/usr/bin/env bash
# Claude Code shell adapter — launch Claude TUI in role's PROJECT_DIR
#
# Claude Code uses the current working directory as project directory; there is no --project-dir flag.
# Permission bypass uses --dangerously-skip-permissions (standalone flag, not a value of --permission-mode).
# SOUL.md is injected via --append-system-prompt-file.
#
# Reference: https://docs.anthropic.com/en/docs/claude-code/cli-reference
set -euo pipefail

PROJECT_DIR="${1:?Usage: shell.sh <project_dir>}"

cd "$PROJECT_DIR"

# If SOUL.md exists, append it as system prompt
if [ -f "SOUL.md" ]; then
    exec claude --dangerously-skip-permissions --append-system-prompt-file SOUL.md
else
    exec claude --dangerously-skip-permissions
fi
