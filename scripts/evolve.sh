#!/usr/bin/env bash
# evolve.sh — Workspace evolution mechanism
#
# Check for changes in the agent/ four primitives within the workspace,
# and decide whether they are workspace-specific adaptations (.runtime/) or general improvements (PR back to main).
#
# Usage:
#   ./scripts/evolve.sh <room/app>            # Check for changes
#   ./scripts/evolve.sh <room/app> --check    # Same as above
#   ./scripts/evolve.sh <room/app> --pr       # Create PR
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

WORKSPACE_PATH="${1:?Usage: evolve.sh <room/app> [--check|--pr]}"
ACTION="${2:---check}"

WORKSPACE_DIR="$REPO_ROOT/.socialware/workspace/$WORKSPACE_PATH"
TEMPLATE_AGENT="$REPO_ROOT/agent"
WORKSPACE_AGENT="$WORKSPACE_DIR/agent"

if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "Error: workspace '$WORKSPACE_PATH' not found at $WORKSPACE_DIR"
    exit 1
fi

echo "Evolve: $WORKSPACE_PATH"
echo "  Workspace: $WORKSPACE_DIR"
echo "  Template:  $TEMPLATE_AGENT"
echo ""

# Compare differences between workspace agent/ and template agent/
CHANGES=0
RUNTIME_CHANGES=0
AGENT_CHANGES=0

echo "Checking for changes..."
echo ""

# Check four primitives for differences (changes under agent/ -> potential general improvements)
for primitive in role scope commitment flow; do
    template_dir="$TEMPLATE_AGENT/$primitive"
    workspace_dir_prim="$WORKSPACE_AGENT/$primitive"

    if [ ! -d "$workspace_dir_prim" ]; then
        continue
    fi

    # diff two directories (ignoring README.md)
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

# Check for changes in .runtime/ (workspace-specific, does not trigger PR)
if [ -d "$WORKSPACE_DIR/.runtime" ]; then
    runtime_files=$(find "$WORKSPACE_DIR/.runtime" -newer "$WORKSPACE_DIR/.runtime" -type f 2>/dev/null | head -20)
    if [ -n "$runtime_files" ]; then
        RUNTIME_CHANGES=1
    fi
fi

# Summary
echo "Summary:"
echo "  Agent changes (→ PR candidate):  $AGENT_CHANGES primitives"
echo "  Runtime changes (workspace-only): $RUNTIME_CHANGES"
echo ""

if [ "$CHANGES" -eq 0 ]; then
    echo "No changes to evolve."
    exit 0
fi

# Routing decision
echo "Evolve routing:"
if [ "$AGENT_CHANGES" -gt 0 ]; then
    echo "  agent/ changes detected → candidate for PR back to main"
    echo ""

    # Replace / in room/app with - for branch name
    BRANCH_NAME=$(echo "$WORKSPACE_PATH" | tr '/' '-')

    if [ "$ACTION" = "--pr" ]; then
        BRANCH="evolve/$BRANCH_NAME-$(date +%Y%m%d-%H%M%S)"
        echo "Creating branch: $BRANCH"

        git -C "$REPO_ROOT" checkout -b "$BRANCH"

        # Copy workspace four primitives changes back to template
        for primitive in role scope commitment flow; do
            workspace_dir_prim="$WORKSPACE_AGENT/$primitive"
            template_dir="$TEMPLATE_AGENT/$primitive"

            if [ -d "$workspace_dir_prim" ]; then
                rsync -av \
                    --exclude="README.md" \
                    --exclude="__pycache__" \
                    "$workspace_dir_prim/" "$template_dir/"
            fi
        done

        git -C "$REPO_ROOT" add agent/
        git -C "$REPO_ROOT" commit -m "evolve($WORKSPACE_PATH): update four primitives from workspace"

        echo ""
        echo "Branch '$BRANCH' created with changes."
        echo "To create PR:"
        echo "  git push -u origin $BRANCH"
        echo "  gh pr create --title 'evolve($WORKSPACE_PATH): update four primitives'"
    else
        echo "Run with --pr to create a branch and PR:"
        echo "  ./scripts/evolve.sh $WORKSPACE_PATH --pr"
    fi
fi
