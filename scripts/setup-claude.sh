#!/usr/bin/env bash
# setup-claude.sh — Configure Claude Code dev environment
# Creates per-skill symlinks: .claude/skills/{name} → ../../agent/skills/{name}
# Follows AutoService pattern: individual symlinks, not whole-directory symlink.
# This allows mixing symlinked agent skills with native Claude Code skills.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="$REPO_ROOT/.claude"
AGENT_SKILLS_DIR="$REPO_ROOT/agent/skills"

echo "Setting up Claude Code for Socialwares..."
echo "Repo: $REPO_ROOT"
echo ""

# 1. Ensure .claude/skills/ exists as a real directory (not a symlink)
if [ -L "$CLAUDE_DIR/skills" ]; then
    echo "⚠ .claude/skills is a symlink (old pattern). Replacing with directory..."
    rm "$CLAUDE_DIR/skills"
fi
mkdir -p "$CLAUDE_DIR/skills"

# 2. Create per-skill symlinks (AutoService pattern)
#    Each skill in agent/skills/ gets its own symlink in .claude/skills/
LINKED=0
for skill_dir in "$AGENT_SKILLS_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    target="../../agent/skills/$skill_name"
    link="$CLAUDE_DIR/skills/$skill_name"

    if [ -L "$link" ]; then
        # Symlink exists, verify target
        current_target=$(readlink "$link")
        if [ "$current_target" = "$target" ]; then
            echo "· $skill_name (already linked)"
        else
            rm "$link"
            ln -s "$target" "$link"
            echo "✓ $skill_name (updated)"
        fi
    elif [ -d "$link" ]; then
        echo "⚠ $skill_name is a real directory, skipping (native skill?)"
    else
        ln -s "$target" "$link"
        echo "✓ $skill_name → $target"
    fi
    ((LINKED++))
done

echo ""
echo "Linked $LINKED skills from agent/skills/ to .claude/skills/"

# 3. Verify agent.yaml exists
if [ ! -f "$REPO_ROOT/agent/agent.yaml" ]; then
    echo "⚠ agent/agent.yaml not found"
else
    echo "✓ agent/agent.yaml found"
fi

# 4. Summary
echo ""
echo "Done. Claude Code is ready for Socialwares development."
echo ""
echo "Next steps:"
echo "  claude                    # start Claude Code"
echo "  ./scripts/launch.sh      # launch agent via SDK"
echo ""
echo "To add native Claude skills (not from agent/):"
echo "  mkdir .claude/skills/my-native-skill/"
echo "  # won't conflict with symlinked agent skills"
