#!/usr/bin/env bash
# Kimi Code CLI shell adapter
#
# Kimi uses --work-dir to specify the working directory.
# --yolo auto-approves all operations.
#
# Reference: https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html
set -euo pipefail

PROJECT_DIR="${1:?Usage: shell.sh <project_dir>}"

exec kimi --work-dir "$PROJECT_DIR" --yolo
