#!/usr/bin/env bash
# Codex CLI shell adapter
#
# Codex 使用 --cd 指定工作目录 (不是 --project-dir)。
# 权限: --full-auto (workspace-write + on-request approvals)
#
# 参考: https://openai.github.io/codex/cli/reference
set -euo pipefail

PROJECT_DIR="${1:?Usage: shell.sh <project_dir>}"

exec codex --cd "$PROJECT_DIR" --full-auto
