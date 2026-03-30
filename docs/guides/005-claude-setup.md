# Claude Code Setup

## socialwares start — Launch Agent with Claude

`socialwares start` is the unified entry point for launching agents. Claude Code is the default adapter.

```bash
socialwares start --role default                     # default adapter (claude)
socialwares start --role default --adapter claude     # explicit
```

### What Happens

1. `socialwares start` reads `.runtime/agents/{role}/` (requires `socialwares deploy` first)
2. Launches Claude Code with the compiled SOUL.md as system prompt
3. Claude Code reads `.runtime/agents/{role}/.claude/skills/` for available skills
4. Hooks (`log_prompt.sh`, `log_tool.sh`) are loaded from `.runtime/agents/{role}/`

### Adapter Configuration

The default adapter is set in `pyproject.toml`:

```toml
[tool.socialwares]
adapter = "claude"     # default adapter
```

Override per-launch:

```bash
socialwares start --role default --adapter codex
socialwares start --role default --adapter kimicode
```

## .runtime/ — Compiled Config

Claude Code reads configuration from `.runtime/agents/{role}/`:

```
.runtime/agents/default/
├── SOUL.md                    ← scope + role merged (system prompt)
├── .claude/
│   └── skills/                ← symlinks to agent/flow/ actions for this role
├── hooks/                     ← log_prompt.sh, log_tool.sh
└── ...
```

- **SOUL.md**: Compiled from `agent/scope/scope.md` + `agent/role/{name}.md`
- **skills/**: Symlinks to `agent/flow/{action}/` directories allowed for this role
- **hooks/**: Capture prompts and tool calls to `.runtime/data/prompts/`

## Multi-Role Launch

```bash
socialwares start --role default,evolver     # tmux panes, one per role
```

## Plugin Setup

If you need Claude Code plugins (agent-setup, superpowers, etc.), install them via the standard Claude Code plugin system:

```bash
claude plugin marketplace add https://github.com/ezagent42/agent-setup
claude plugin install agent-setup@agent-setup --scope project
```

## Workflow Summary

```bash
# 1. Create project
socialwares new my-app && cd my-app

# 2. Install dependencies
uv sync

# 3. Compile
socialwares deploy

# 4. Start Claude Code agent
socialwares start --role default

# 5. Iterate
#    Edit socialware.py + agent/ → socialwares deploy → socialwares start
```
