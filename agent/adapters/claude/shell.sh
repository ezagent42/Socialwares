#!/usr/bin/env bash
# Claude Code shell adapter — launch Claude TUI with role's PROJECT_DIR
set -euo pipefail

PROJECT_DIR="${1:?Usage: shell.sh <project_dir>}"

exec claude --project-dir "$PROJECT_DIR" --permission-mode bypassPermissions
