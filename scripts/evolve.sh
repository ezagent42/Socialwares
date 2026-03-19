#!/usr/bin/env bash
# evolve.sh — Workspace 进化机制
#
# 检查 workspace 中 agent/ 四原语的变更，
# 决定是 workspace 特定适配 (.runtime/) 还是通用改进 (PR 回 main)。
#
# Usage:
#   ./scripts/evolve.sh <workspace_name>
#   ./scripts/evolve.sh my-app
#   ./scripts/evolve.sh my-app --check    # 只检查，不执行
#   ./scripts/evolve.sh my-app --pr       # 创建 PR
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

WORKSPACE_NAME="${1:?Usage: evolve.sh <workspace_name> [--check|--pr]}"
ACTION="${2:---check}"

WORKSPACE_DIR="$REPO_ROOT/.socialware/workspace/$WORKSPACE_NAME"
TEMPLATE_AGENT="$REPO_ROOT/agent"
WORKSPACE_AGENT="$WORKSPACE_DIR/agent"

if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "Error: workspace '$WORKSPACE_NAME' not found at $WORKSPACE_DIR"
    exit 1
fi

echo "Evolve: $WORKSPACE_NAME"
echo "  Workspace: $WORKSPACE_DIR"
echo "  Template:  $TEMPLATE_AGENT"
echo ""

# 比较 workspace agent/ 和模板 agent/ 的差异
CHANGES=0
RUNTIME_CHANGES=0
AGENT_CHANGES=0

echo "Checking for changes..."
echo ""

# 检查四原语差异 (agent/ 下的变更 → 可能是通用改进)
for primitive in role scope commitment flow; do
    template_dir="$TEMPLATE_AGENT/$primitive"
    workspace_dir_prim="$WORKSPACE_AGENT/$primitive"

    if [ ! -d "$workspace_dir_prim" ]; then
        continue
    fi

    # diff 两个目录 (忽略 README.md)
    diff_output=$(diff -rq \
        --exclude="README.md" \
        --exclude="__pycache__" \
        --exclude=".DS_Store" \
        "$template_dir" "$workspace_dir_prim" 2>/dev/null || true)

    if [ -n "$diff_output" ]; then
        echo "  [agent/$primitive] Changes detected:"
        echo "$diff_output" | sed 's/^/    /'
        echo ""
        AGENT_CHANGES=$((AGENT_CHANGES + 1))
        CHANGES=$((CHANGES + 1))
    fi
done

# 检查 .runtime/ 中的变更 (workspace 特定，不触发 PR)
if [ -d "$WORKSPACE_DIR/.runtime" ]; then
    runtime_files=$(find "$WORKSPACE_DIR/.runtime" -newer "$WORKSPACE_DIR/.runtime" -type f 2>/dev/null | head -20)
    if [ -n "$runtime_files" ]; then
        RUNTIME_CHANGES=1
    fi
fi

# 汇总
echo "Summary:"
echo "  Agent changes (→ PR candidate):  $AGENT_CHANGES primitives"
echo "  Runtime changes (workspace-only): $RUNTIME_CHANGES"
echo ""

if [ "$CHANGES" -eq 0 ]; then
    echo "No changes to evolve."
    exit 0
fi

# 路由决策
echo "Evolve routing:"
if [ "$AGENT_CHANGES" -gt 0 ]; then
    echo "  agent/ changes detected → candidate for PR back to main"
    echo ""

    if [ "$ACTION" = "--pr" ]; then
        # 创建 branch 和 PR
        BRANCH="evolve/$WORKSPACE_NAME-$(date +%Y%m%d-%H%M%S)"
        echo "Creating branch: $BRANCH"

        git -C "$REPO_ROOT" checkout -b "$BRANCH"

        # 复制 workspace 的四原语变更回模板
        for primitive in role scope commitment flow; do
            workspace_dir_prim="$WORKSPACE_AGENT/$primitive"
            template_dir="$TEMPLATE_AGENT/$primitive"

            if [ -d "$workspace_dir_prim" ]; then
                # 复制变更文件 (不覆盖 README.md)
                rsync -av \
                    --exclude="README.md" \
                    --exclude="__pycache__" \
                    "$workspace_dir_prim/" "$template_dir/"
            fi
        done

        git -C "$REPO_ROOT" add agent/
        git -C "$REPO_ROOT" commit -m "evolve($WORKSPACE_NAME): update four primitives from workspace"

        echo ""
        echo "Branch '$BRANCH' created with changes."
        echo "To create PR:"
        echo "  git push -u origin $BRANCH"
        echo "  gh pr create --title 'evolve($WORKSPACE_NAME): update four primitives'"
    else
        echo "Run with --pr to create a branch and PR:"
        echo "  ./scripts/evolve.sh $WORKSPACE_NAME --pr"
    fi
fi
