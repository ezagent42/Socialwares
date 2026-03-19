#!/usr/bin/env bash
# Codex CLI shell adapter
set -euo pipefail

PROJECT_DIR="${1:?Usage: shell.sh <project_dir>}"

exec codex --project-dir "$PROJECT_DIR"
