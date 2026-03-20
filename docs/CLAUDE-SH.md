# claude.sh — Claude Code Launcher

`claude.sh` is a tmux-based launcher for Claude Code sessions, provided by the [agent-setup](https://github.com/ezagent42/agent-setup) plugin system.

## What It Does

1. Sources shell configuration (PATH, env vars)
2. **Auto-installs agent-setup plugin** on first run (marketplace registration + plugin install)
3. Launches Claude Code inside a tmux session (SSH disconnect resilience)
4. Supports 3 modes: Interactive, Interactive+Worktree, Remote Control

## Usage

### From Repo Root (template development)

```bash
./claude.sh
```

First run:
- Registers agent-setup marketplace
- Installs agent-setup plugin for this project
- Opens Claude Code in tmux

Inside Claude Code, run `/agent-setup:init` to interactively configure:
- Hooks (enforce-tools, session-start)
- Additional plugins (superpowers, impeccable, etc.)
- MCP servers

### From a Workspace (via dev role)

The dev role's `setup_claude` skill uses claude.sh to configure the workspace's `.runtime/agents/dev/.claude/`:

```bash
cd .socialware/workspace/my-team/my-app
./agent/deploy.sh
./agent/start.sh --role dev
# In Claude Code: say "setup claude"
```

This installs agent-setup into the dev role's isolated PROJECT_DIR.

## Modes

| Mode | Description | When to Use |
|------|-------------|-------------|
| **[1] Interactive** | Standard Claude Code session | Daily development |
| **[2] Interactive+Worktree** | Isolated git branch for feature work | Feature branches |
| **[3] Remote Control** | Continue from phone/browser | On the go |

## Session Management

claude.sh uses tmux for session persistence:

- **Detach**: `Ctrl+b, d` (session keeps running)
- **Reattach**: Run `./claude.sh` again — it detects existing sessions
- **Multiple sessions**: claude.sh manages per-project sessions (`claude-{project}-*`)

If iTerm2 is detected, uses `tmux -CC` for native tab integration.

## What Gets Installed

After `/agent-setup:init`:

```
.claude/
├── settings.json          ← Permission mode, enabled plugins
├── settings.local.json    ← Hooks configuration
├── mcp.json               ← MCP server configuration (e.g., context7)
└── skills/                ← Skills from installed plugins
```

### Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `enforce-tools.sh` | PreToolUse:Bash | Block pip/npm, suggest uv/pnpm |
| `session-start.sh` | SessionStart | Health check on each session start |

## Environment Variables

Set in `claude.local.sh` (gitignored) or `.mcp.env`:

```bash
# claude.local.sh — user-local overrides
export ANTHROPIC_API_KEY=sk-...

# .mcp.env — MCP server secrets
CONTEXT7_API_KEY=...
```

## Relationship to agent/start.sh

| | `claude.sh` | `agent/start.sh` |
|---|---|---|
| **Purpose** | Bootstrap Claude Code environment (plugins, hooks, MCP) | Launch agent with specific role and SOUL.md |
| **Working dir** | Repo root (or wherever claude.sh lives) | .runtime/agents/{role}/ |
| **Installs plugins** | Yes (agent-setup) | No |
| **Uses SOUL.md** | No | Yes (--append-system-prompt-file) |
| **When** | First-time setup, plugin management | Daily agent usage |
