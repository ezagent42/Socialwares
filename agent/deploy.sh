#!/usr/bin/env bash
# deploy.sh — 编译四原语 → .runtime/
# 为每个 role 生成独立的 $PROJECT_DIR (含 .claude/skills/, SOUL.md)
# .runtime/data/ 是共享数据目录
# .runtime/agents/{role}/ 是每个 role 的隔离环境
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$AGENT_DIR/.." && pwd)"

# 默认 workspace
WORKSPACE="${1:-.socialware/workspace/default}"
if [[ "$WORKSPACE" = /* ]]; then
    RUNTIME_DIR="$WORKSPACE/.runtime"
else
    RUNTIME_DIR="$REPO_ROOT/$WORKSPACE/.runtime"
fi

echo "Deploying four primitives → $RUNTIME_DIR"
echo ""

# 1. 创建 .runtime/ 结构
mkdir -p "$RUNTIME_DIR/data/Files"
mkdir -p "$RUNTIME_DIR/data/Sqlite"

# 2. 为每个 role 生成独立 PROJECT_DIR
for role_dir in "$AGENT_DIR"/role/*/; do
    [ -d "$role_dir" ] || continue
    role_name=$(basename "$role_dir")
    role_runtime="$RUNTIME_DIR/agents/$role_name"

    echo "  Role: $role_name"

    # 创建目录
    mkdir -p "$role_runtime/.claude/skills"
    mkdir -p "$role_runtime/.claude/hooks"

    # 合并 SOUL.md: scope/SOUL.md + role/{name}/SOUL.md
    {
        cat "$AGENT_DIR/scope/SOUL.md" 2>/dev/null || true
        echo ""
        echo "---"
        echo ""
        cat "$role_dir/SOUL.md" 2>/dev/null || true
    } > "$role_runtime/SOUL.md"

    # 软连接 flow/ 下的每个 skill (使用相对路径，跨机器可移植)
    for skill_dir in "$AGENT_DIR"/flow/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")
        link="$role_runtime/.claude/skills/$skill_name"

        # 计算从 link 位置到 skill_dir 的相对路径
        # link: .runtime/agents/{role}/.claude/skills/{skill}
        # target: agent/flow/{skill}/
        # 相对: ../../../../../agent/flow/{skill}
        link_dir=$(dirname "$link")
        target=$(python3 -c "import os.path; print(os.path.relpath('$skill_dir', '$link_dir'))")

        # 删除旧连接
        [ -L "$link" ] && rm "$link"
        [ -d "$link" ] && rm -rf "$link"

        ln -s "$target" "$link"
    done

    # 复制 commitment eval 配置
    if [ -f "$AGENT_DIR/commitment/eval.yaml" ]; then
        cp "$AGENT_DIR/commitment/eval.yaml" "$role_runtime/eval.yaml"
    fi

    echo "    SOUL.md: $(wc -l < "$role_runtime/SOUL.md") lines"
    echo "    Skills: $(ls "$role_runtime/.claude/skills/" 2>/dev/null | wc -l)"
    echo ""
done

echo "Deploy complete."
echo "  Data: $RUNTIME_DIR/data/"
echo "  Agents: $RUNTIME_DIR/agents/"
echo ""
echo "Start with: ./agent/start.sh --role <role_name>"
