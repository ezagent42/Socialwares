#!/usr/bin/env bash
# start.sh — 启动 SwSim 的 Claude Code 会话（bypass 权限模式）
#
# 用法:
#   ./start.sh
#
# 效果:
#   以 dangerouslySkipPermissions 模式启动 Claude Code，
#   所有工具调用自动批准，适合模拟测试场景。

set -euo pipefail
cd "$(dirname "$0")"

exec claude --dangerously-skip-permissions
