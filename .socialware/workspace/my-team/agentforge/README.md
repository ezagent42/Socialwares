# AgentForge

Agent 创建与配置管理平台。通过 Chat 对话或 Dashboard UI 创建、编辑、导出和导入 AI Agent 配置，支持 5 种主流格式互转。

## Quick Start

### Backend

```bash
cd .socialware/workspace/my-team/agentforge

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET

# 运行测试
uv run pytest -v

# 启动服务
uv run uvicorn src.app:app --port 8001
```

### Frontend

```bash
cd app

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

浏览器访问 `http://localhost:3000`，通过 GitHub 登录后即可使用。

## Available Commands

在 Chat 面板中输入以下命令：

| 命令 | 说明 |
|------|------|
| `/create-agent` | 3 步向导创建 Agent（名称 → 身份描述 → 技能） |
| `/list-agents` | 列出所有 Agent（含示例 Agent） |
| `/add-skill` | 为 Agent 添加技能（手动 / search / url） |
| `/find-skill` | 搜索本地和内置技能库 |
| `/export-agent` | 导出 Agent 配置（选择格式后下载 zip） |
| `/import-agent` | 导入 Agent 配置包 |
| `/delete-agent` | 删除 Agent（需确认） |

也支持自然语言：`创建一个 task-manager Agent`、`列出所有 Agent`、`导出 chatbot`。

## Export / Import Formats

| 格式 | 输出结构 | 适用平台 |
|------|----------|----------|
| **gitagent** | `agent.yaml` + `SOUL.md` + `skills/` | GitAgent 标准，跨平台分享 |
| **claude-code** | `CLAUDE.md` + `.claude/skills/` | Claude Code |
| **codex** | `AGENTS.md` + `.agents/skills/` | OpenAI Codex |
| **cursor** | `.cursor/rules` | Cursor |
| **socialwares** | `agent/role/` + `flow/` + `scope.md` + `commitment.yaml` | Socialwares 四原语 |

导入时自动检测格式，无需手动指定。导出 → 导入 roundtrip 已通过全部 5 种格式测试。

## Architecture

```
Frontend (Next.js 15 / React 19 / Tailwind 4)
  ├── Chat Panel ─── POST /api/chat/send ──→ SessionManager
  ├── Dashboard ──── UIAction (ui_action) ──→ SessionManager
  └── Sidebar ────── Theme / Auth / Navigation
                                                  │
Backend (FastAPI / aiosqlite)                     ▼
  ├── SessionManager ── 多步向导 + 意图匹配 + Claude SDK
  ├── CRUD ──────────── agent_crud / skill_crud / find_skill
  ├── Export ─────────── 5 格式适配器 → zip 下载
  ├── Import ─────────── 自动检测 → 解析 → 写入 DB
  └── Auth ──────────── GitHub OAuth + Session Cookie

Database (SQLite)
  ├── users / sessions ── 用户认证
  ├── agents ──────────── name + role_md + is_example
  ├── skills ──────────── agent_id + name + skill_md
  └── chat_history ────── 会话记录
```

### Dual Interaction

用户通过两种方式与系统交互，统一经 SessionManager 处理：

- **Chat 输入** — 自然语言或 `/command` 斜杠命令
- **UI 操作** — Dashboard 按钮点击，序列化为 ````ui_action` JSON 发送

SessionManager 返回 SSE 流，包含 `text`（文本）和 `structured`（结构化数据）事件，前端 `StructuredBlockRenderer` 根据 `type + action` 分发渲染对应组件。

### Claude SDK Integration

当配置了 `ANTHROPIC_API_KEY` 时，非斜杠命令的自然语言消息会路由到 Claude Agent 处理。Agent 读取 `.runtime/agents/default/SOUL.md` 和技能定义，通过 Bash tool 调用 CRUD CLI 执行操作。未配置时回退到内置意图匹配。

## Project Structure

```
agentforge/
├── src/
│   ├── app.py              # FastAPI 入口 + API 路由
│   ├── db.py               # SQLite 初始化
│   ├── auth.py             # GitHub OAuth
│   ├── session.py          # SessionManager (多步向导 + 意图匹配)
│   ├── claude_adapter.py   # Claude SDK 适配器
│   ├── response_parser.py  # json:structured 解析
│   ├── seed.py             # 示例 Agent 数据
│   ├── crud/
│   │   ├── agent_crud.py   # Agent CRUD
│   │   ├── skill_crud.py   # Skill CRUD
│   │   ├── find_skill.py   # 技能搜索
│   │   ├── export.py       # 导出调度
│   │   ├── import_agent.py # 导入 + 格式检测
│   │   └── cli.py          # CLI (供 Agent Bash tool 调用)
│   └── adapters/           # 5 种导出格式适配器
├── app/                    # Next.js 前端
│   └── src/
│       ├── components/     # React 组件
│       └── lib/            # Store + Types + Utils
├── agent/                  # 四原语定义
│   ├── role/               # 角色 Markdown
│   ├── flow/               # 技能 SKILL.md + flow.yaml
│   ├── scope/              # 能力边界
│   └── commitment/         # 评估指标
├── tests/                  # 64+ 测试用例
└── Makefile                # deploy / start / test
```

## Testing

```bash
# 运行全部测试
uv run pytest -v

# 运行特定模块
uv run pytest tests/test_chat_api.py -v
uv run pytest tests/test_e2e_export_import.py -v

# 包含 SDK 集成测试（需要 API key）
ANTHROPIC_API_KEY=sk-xxx uv run pytest tests/test_agent_integration.py -v
```

## License

Internal project — Socialwares workspace.
