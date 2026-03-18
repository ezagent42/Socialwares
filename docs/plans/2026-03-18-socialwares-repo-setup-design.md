# Socialwares 仓库初始化设计

> 为 `git@github.com:ezagent42/Socialwares.git`（空仓库）完成初始化：
> Claude 开发配置 + GitAgent 格式的 agent/ 目录 + 多平台适配脚本。
>
> **日期**: 2026-03-18
> **参与者**: yaosh + Claude

---

## 背景

Socialwares MonoRepo 是 Socialware App 的集中开发仓库。每个 App（TaskArena、AgentForge 等）是独立软件，面向 agent 暴露 API，通过 Role/Flow/Commitment/Arena 四原语进行调用。

底层 bus 负责多 agent/subagent 消息传递（P2P IM 模式），agent/ 目录定义本机 agent 配置，通过 adapter 连接不同 Agent SDK（Claude、Codex、KimiCode）。

### 参考源

- **GitAgent** (gitagent.sh): agent.yaml + SOUL.md + skills/ + tools/ + agents/ 标准格式
- **AutoService** (ezagent42/autoservices): SKILL.md + config.yaml + scripts/ + _shared/ + symlink 运行时模式
- **agent-setup** (ezagent42/agent-setup): Claude Code 插件系统，hooks/commands/marketplace/claude.sh

---

## 两个工作

### 工作一：从 agent-setup 配置 Claude 开发环境

**目标**: 让 Socialwares 仓库的 Claude Code 开发环境可用，包含基础 hooks、settings、MCP 配置。

**来源**: `git@github.com:ezagent42/agent-setup.git`

**需要的内容**:

```
从 agent-setup 提取:
├── .claude/
│   ├── settings.json          ← 权限、插件、teammate 模式
│   └── mcp.json               ← Context7 MCP 服务器
├── hooks/                     ← 可选: enforce-tools.sh (uv/pnpm 强制)
└── claude.sh                  ← 项目启动器模板 (tmux 集成)
```

**适配调整**:
- `settings.json`: 保留 bypassPermissions + enabledPlugins，按需调整
- `mcp.json`: 保留 context7，后续加 SW app 的 MCP server
- `CLAUDE.md`: 全新编写，面向 Socialwares 项目
- hooks: 保留 enforce-tools.sh (强制 uv 不用 pip)，session-start.sh 适配

**产出**: 推送到 Socialwares 仓库的 main 分支。

---

### 工作二：配置 agent/ 目录 + 脚本

**目标**: 按 GitAgent 格式 + AutoService 运行时模式，创建 agent/ 目录，提供 symlink 脚本和多平台适配。

**完整目录结构**:

```
Socialwares/
│
├── agent/                          ← GitAgent 格式 (本机 agent 定义)
│   ├── agent.yaml                  ← 身份、模型、适配器、依赖
│   ├── SOUL.md                     ← 人格: Socialwares 开发者 agent
│   ├── RULES.md                    ← 约束: 开发规范
│   │
│   ├── skills/                     ← 能力模块
│   │   ├── _shared/                ← 共享库 (AutoService 模式)
│   │   │   ├── __init__.py
│   │   │   ├── config.py           ← 配置加载器
│   │   │   ├── sw_client.py        ← SW App API 通用客户端
│   │   │   └── scripts/
│   │   │       └── call_api.py     ← 通用 API 调用脚本
│   │   │
│   │   ├── taskarena/              ← 通用: TaskArena API 绑定
│   │   │   ├── SKILL.md            ← 技能文档: 怎么用 TA
│   │   │   ├── config.yaml         ← {api_url, namespace, roles}
│   │   │   ├── scripts/
│   │   │   │   ├── create_task.py
│   │   │   │   ├── update_task.py
│   │   │   │   ├── query_task.py
│   │   │   │   └── review_task.py
│   │   │   └── references/
│   │   │       └── taskarena-api.md
│   │   │
│   │   ├── agentforge/             ← 通用: AgentForge API 绑定
│   │   │   ├── SKILL.md
│   │   │   ├── config.yaml
│   │   │   ├── scripts/
│   │   │   │   ├── spawn_agent.py
│   │   │   │   ├── wake_agent.py
│   │   │   │   ├── list_agents.py
│   │   │   │   ├── download_template.py
│   │   │   │   └── generate_from_roles.py
│   │   │   └── references/
│   │   │       └── agentforge-api.md
│   │   │
│   │   └── dev/                    ← 特性: 本仓库开发专用
│   │       ├── SKILL.md            ← 开发工作流指南
│   │       └── references/
│   │           └── four-primitives.md
│   │
│   ├── tools/                      ← MCP 工具定义 (GitAgent 标准)
│   │   ├── taskarena-api.yaml      ← TA API 的 MCP 工具 schema
│   │   └── agentforge-api.yaml    ← AF API 的 MCP 工具 schema
│   │
│   ├── knowledge/                  ← 参考文档
│   │   ├── index.yaml              ← 文档索引 (GitAgent 标准)
│   │   ├── socialware-concepts.md  ← SW 核心概念
│   │   └── four-primitives.md      ← 四原语详解
│   │
│   ├── agents/                     ← 子 agent 定义
│   │   ├── .gitkeep               ← 初始为空，AF 下载/生成到这里
│   │   └── README.md              ← 说明: 如何添加子 agent
│   │
│   ├── adapters/                   ← SDK 启动模板
│   │   ├── base.py                 ← 通用 adapter 接口
│   │   ├── claude/
│   │   │   ├── launcher.py         ← Claude Agent SDK 启动器
│   │   │   ├── multi_launcher.py   ← 多 agent 编排启动
│   │   │   └── requirements.txt
│   │   ├── codex/
│   │   │   ├── launcher.py         ← OpenAI Agents SDK 启动器
│   │   │   └── requirements.txt
│   │   └── kimicode/
│   │       ├── launcher.py         ← Kimi 适配器
│   │       └── requirements.txt
│   │
│   ├── hooks/
│   │   └── hooks.yaml              ← GitAgent 生命周期钩子
│   │
│   └── memory/
│       ├── MEMORY.md               ← 持久记忆 (GitAgent 标准)
│       └── memory.yaml
│
├── apps/                           ← SW App 本体 (服务端)
│   ├── taskarena/
│   │   ├── src/                    ← Python API server
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── agentforge/
│       ├── src/
│       ├── pyproject.toml
│       └── README.md
│
├── scenarios/                      ← 多 agent 场景编排
│   ├── README.md
│   └── examples/
│       └── task-review.yaml        ← 示例场景
│
├── scripts/                        ← 运维/适配脚本
│   ├── setup-claude.sh             ← symlink agent/skills/ → .claude/skills/
│   ├── setup-codex.sh              ← 导出 codex 适配配置
│   ├── setup-kimicode.sh           ← 导出 kimicode 适配配置
│   ├── launch.sh                   ← 单 agent 启动 (选择 adapter)
│   └── launch-scenario.sh          ← 多 agent 场景启动
│
├── .claude/                        ← Claude Code CLI 配置
│   ├── settings.json               ← 从 agent-setup 继承
│   ├── mcp.json                    ← MCP 服务器配置
│   ├── CLAUDE.md                   ← 项目指南
│   └── skills/ → ../agent/skills/  ← symlink (setup-claude.sh 创建)
│
├── .gitignore
├── CLAUDE.md                       ← 顶层项目指南
├── README.md
└── pyproject.toml                  ← 顶层 monorepo 配置 (uv workspace)
```

---

## agent.yaml 设计

```yaml
# agent/agent.yaml
name: socialwares-dev
version: "0.1.0"
description: "Socialwares MonoRepo 开发者 agent"
spec_version: "0.1.0"

author: ezagent42
license: proprietary
tags: [socialware, development, multi-agent]

model:
  preferred: claude-sonnet-4-6
  fallback:
    - claude-haiku-4-5-20251001

skills:
  - _shared
  - taskarena
  - agentforge
  - dev

tools:
  - taskarena-api
  - agentforge-api

dependencies: []

runtime:
  max_turns: 100
  timeout: 3600
```

---

## 通用 vs 特性区分

```
通用 (任何 agent 都用):
  agent/skills/taskarena/     ← "怎么用 TaskArena API"
  agent/skills/agentforge/    ← "怎么用 AgentForge API"
  agent/skills/_shared/       ← 共享库
  agent/tools/                ← MCP 工具定义
  agent/knowledge/            ← SW 概念文档

特性 (特定 agent 专用):
  agent/agent.yaml            ← 这个 agent 的身份
  agent/SOUL.md               ← 这个 agent 的人格
  agent/skills/dev/           ← 开发专用技能
  agent/agents/               ← 从 AF 下载的子 agent 模板
  agent/adapters/             ← 平台适配 (每个平台不同)
```

---

## setup-claude.sh 脚本设计

```bash
#!/usr/bin/env bash
# scripts/setup-claude.sh
# 配置 Claude Code 开发环境: symlink agent/skills/ → .claude/skills/

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="$REPO_ROOT/.claude"
AGENT_DIR="$REPO_ROOT/agent"

# 1. 确保 .claude/ 存在
mkdir -p "$CLAUDE_DIR"

# 2. symlink skills
if [ -L "$CLAUDE_DIR/skills" ]; then
    rm "$CLAUDE_DIR/skills"
fi
ln -s "../agent/skills" "$CLAUDE_DIR/skills"
echo "✓ .claude/skills/ → agent/skills/"

# 3. 复制 settings.json 和 mcp.json (如果不存在)
for f in settings.json mcp.json; do
    if [ ! -f "$CLAUDE_DIR/$f" ]; then
        cp "$REPO_ROOT/scripts/templates/$f" "$CLAUDE_DIR/$f"
        echo "✓ .claude/$f created"
    else
        echo "· .claude/$f already exists, skipping"
    fi
done

echo "Done. Claude Code is ready for Socialwares development."
```

---

## 两条使用路径

```
开发路径 (人在终端前):
  1. git clone Socialwares
  2. ./scripts/setup-claude.sh
  3. claude                          ← Claude Code CLI
  4. /taskarena create "实现 AF API"   ← 自举: 用 TA 管理开发
  5. 写代码...

运行路径 (agent 自动跑):
  1. ./scripts/launch.sh --adapter claude
     → agent/adapters/claude/launcher.py
     → 读 agent.yaml + SOUL.md + skills/
     → Claude Agent SDK 启动 headless agent

  2. ./scripts/launch-scenario.sh scenarios/task-review.yaml
     → agent/adapters/claude/multi_launcher.py
     → 启动 3 个 agent，通过 bus 协作

  3. ./scripts/setup-codex.sh
     → gitagent export --format openai
     → 或直接调 agent/adapters/codex/launcher.py
```

---

## 自举循环

```
Iteration 0: 基础 Claude Code 配置 (从 agent-setup)
  → 可以写代码

Iteration 1: TaskArena skills 写好
  → 可以 /taskarena create/update/review
  → 用 TA 管理自己的开发任务

Iteration 2: AgentForge skills 写好
  → 可以 /agentforge spawn/wake/list
  → 用 AF 管理开发 agent (code-reviewer 等)

Iteration 3: adapters 写好
  → 可以 launch.sh 启动 headless agent
  → 多 agent 协作开发

每一步都在用上一步的产出开发下一步。
```
