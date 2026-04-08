#!/usr/bin/env bash
# Codex CLI shell adapter
#
# Codex uses --cd to specify the working directory (not --project-dir).
# Permissions: --full-auto (workspace-write + on-request approvals)
#
# Reference: https://openai.github.io/codex/cli/reference
set -euo pipefail

PROJECT_DIR="${1:?Usage: shell.sh <project_dir>}"

exec codex --cd "$PROJECT_DIR" --full-auto
