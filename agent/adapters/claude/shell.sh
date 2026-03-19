#!/usr/bin/env bash
# Claude Code shell adapter — launch Claude TUI in role's PROJECT_DIR
#
# Claude Code 使用当前工作目录作为项目目录，没有 --project-dir 标志。
# 权限跳过使用 --dangerously-skip-permissions (独立标志，不是 --permission-mode 的值)。
# SOUL.md 通过 --append-system-prompt-file 注入。
#
# 参考: https://docs.anthropic.com/en/docs/claude-code/cli-reference
set -euo pipefail

PROJECT_DIR="${1:?Usage: shell.sh <project_dir>}"

cd "$PROJECT_DIR"

# 如果有 SOUL.md，作为 system prompt 追加
if [ -f "SOUL.md" ]; then
    exec claude --dangerously-skip-permissions --append-system-prompt-file SOUL.md
else
    exec claude --dangerously-skip-permissions
fi
