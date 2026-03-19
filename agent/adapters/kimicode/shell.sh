#!/usr/bin/env bash
# Kimi Code CLI shell adapter
#
# Kimi 使用 --work-dir 指定工作目录。
# --yolo 自动批准所有操作。
#
# 参考: https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html
set -euo pipefail

PROJECT_DIR="${1:?Usage: shell.sh <project_dir>}"

exec kimi --work-dir "$PROJECT_DIR" --yolo
