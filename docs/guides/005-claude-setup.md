# Claude Code Setup

## claude.sh — First-Time Setup

`claude.sh` at the repo root is a tmux-based launcher that auto-installs the [agent-setup](https://github.com/ezagent42/agent-setup) plugin.

```bash
# From repo root (first-time template setup)
./claude.sh
# Inside Claude Code: /agent-setup:init
```

### What Gets Installed

- **Hooks**: enforce-tools (block pip/npm), session-start health check
- **Plugins**: superpowers, impeccable, etc. (user selects)
- **MCP**: context7 and other servers
- **Settings**: permission mode, enabled plugins

### Modes

| Mode | Description |
|------|-------------|
| [1] Interactive | Standard Claude Code session |
| [2] Interactive + Worktree | Isolated git branch |
| [3] Remote Control | Continue from phone/browser |

## Dev Role — Workspace Setup

For workspaces, use the dev role instead of claude.sh:

```bash
cd .socialware/workspace/my-team/my-app
make start ROLE=dev
# In Claude Code: "setup claude"
```

The dev role's `setup_claude` skill runs two plugin commands directly (no claude.sh needed):
```bash
claude plugin marketplace add https://github.com/ezagent42/agent-setup
claude plugin install agent-setup@agent-setup --scope project
```

This sets up the Claude Code environment within the workspace context, using the workspace's `.runtime/agents/dev/` as the project directory.

## claude.sh vs dev role vs start.sh

| | claude.sh | dev role | start.sh |
|---|---|---|---|
| Purpose | Bootstrap plugins | Setup + navigate | Launch any role |
| Where | Repo root | Workspace | Workspace |
| Installs plugins | Yes | Yes (via skill) | No |
| Uses SOUL.md | No | Yes | Yes |
| When | First-time only | Per-workspace setup | Daily use |
