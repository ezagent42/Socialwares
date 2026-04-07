#!/usr/bin/env python3
"""Claude Agent SDK adapter.

Uses claude-agent-sdk for programmatic agent interaction.
Requires: uv pip install 'claude-agent-sdk>=0.1.16'

v0.3.0: yield MessageEvent instead of serialize(msg) dicts.
v0.3.1: Use query() instead of ClaudeSDKClient for reliability on Windows.

Reference:
- SDK: https://github.com/anthropics/claude-agent-sdk-python
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig, EventKind, MessageEvent, proxy_env


class ClaudeAdapter(BaseAdapter):
    """Claude Agent SDK adapter."""

    def launch_shell(self) -> None:
        """Launch Claude Code TUI via CLI."""
        import subprocess
        cmd = ["claude", "--dangerously-skip-permissions"]

        soul_path = self.config.project_dir / "SOUL.md"
        if soul_path.exists():
            cmd.extend(["--append-system-prompt-file", str(soul_path)])

        subprocess.run(cmd, cwd=str(self.config.project_dir))

    async def launch_sdk(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        max_turns: int | None = None,
    ) -> AsyncIterator[MessageEvent]:
        """Launch via Claude Agent SDK, yielding MessageEvent.

        Uses query() for stateless one-shot interaction (reliable on Windows).

        Maps Claude SDK message types to platform-agnostic EventKind:
        - AssistantMessage/TextBlock     -> TEXT_DELTA
        - AssistantMessage/ToolUseBlock  -> TOOL_START or SUBAGENT_START
        - UserMessage (tool result)      -> TOOL_RESULT or SUBAGENT_RESULT
        - ResultMessage                  -> SESSION_END
        """
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions
            from claude_agent_sdk.types import (
                AssistantMessage,
                ResultMessage,
                UserMessage,
                TextBlock,
                ToolUseBlock,
            )
        except ImportError:
            yield MessageEvent(
                kind=EventKind.ERROR,
                content="claude-agent-sdk not installed. Install: uv pip install 'claude-agent-sdk>=0.1.16'",
            )
            return

        cli_path = shutil.which("claude") or shutil.which("claude.CMD")

        # Use --append-system-prompt-file instead of system_prompt param
        # to avoid Windows SDK bug where newlines in system_prompt break JSON pipe.
        extra_args: dict[str, str | None] = {}
        soul_file = self.config.project_dir / "SOUL.md"
        if soul_file.exists():
            extra_args["append-system-prompt-file"] = str(soul_file)

        options = ClaudeAgentOptions(
            cwd=str(self.config.workspace_root),
            setting_sources=None,  # Disable auto-loading .claude/settings (hooks cause init timeout)
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"],
            permission_mode="bypassPermissions",
            resume=session_id,
            max_turns=max_turns,
            env=proxy_env(),
            extra_args=extra_args,
        )
        if cli_path:
            options.cli_path = cli_path

        yield MessageEvent(kind=EventKind.TURN_START)

        # Track which ToolUseBlock.id maps to Agent (subagent) calls
        _agent_tool_ids: set[str] = set()

        async for message in query(prompt=prompt, options=options):

            if isinstance(message, AssistantMessage):
                # Skip sub-agent internal messages
                if getattr(message, "parent_tool_use_id", None) is not None:
                    continue

                for block in message.content:
                    if isinstance(block, TextBlock) and block.text:
                        yield MessageEvent(
                            kind=EventKind.TEXT_DELTA,
                            content=block.text,
                            raw=block,
                        )
                    elif isinstance(block, ToolUseBlock):
                        if block.name == "Agent":
                            _agent_tool_ids.add(block.id)
                            yield MessageEvent(
                                kind=EventKind.SUBAGENT_START,
                                tool_name=block.input.get("description", "agent"),
                                tool_input=block.input,
                                raw=block,
                            )
                        else:
                            yield MessageEvent(
                                kind=EventKind.TOOL_START,
                                tool_name=block.name,
                                tool_input=block.input,
                                raw=block,
                            )

            elif isinstance(message, UserMessage):
                # Skip sub-agent internal tool results
                parent_id = getattr(message, "parent_tool_use_id", None)
                if parent_id is not None:
                    continue

                result_str = str(getattr(message, "tool_use_result", "") or "")[:500]

                # Check if this is a subagent result by matching tool_use_id
                uuid = getattr(message, "uuid", None)
                if uuid and uuid in _agent_tool_ids:
                    _agent_tool_ids.discard(uuid)
                    yield MessageEvent(
                        kind=EventKind.SUBAGENT_RESULT,
                        tool_output=result_str,
                        raw=message,
                    )
                else:
                    yield MessageEvent(
                        kind=EventKind.TOOL_RESULT,
                        tool_output=result_str,
                        raw=message,
                    )

            elif isinstance(message, ResultMessage):
                yield MessageEvent(
                    kind=EventKind.SESSION_END,
                    session_id=message.session_id,
                    metadata={
                        "duration_ms": message.duration_ms,
                        "num_turns": message.num_turns,
                        "is_error": message.is_error,
                        "total_cost_usd": message.total_cost_usd,
                    },
                    raw=message,
                )
                if message.is_error:
                    result_text = getattr(message, "result", "") or ""
                    if result_text:
                        yield MessageEvent(
                            kind=EventKind.ERROR,
                            content=result_text,
                            raw=message,
                        )

        yield MessageEvent(kind=EventKind.TURN_END)


if __name__ == "__main__":
    import argparse
    import asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="Path to .runtime/agents/{role}/")
    parser.add_argument("--prompt", default="You are ready.", help="Initial prompt")
    args = parser.parse_args()

    config = RoleConfig.from_runtime(args.project_dir)
    adapter = ClaudeAdapter(config)

    async def main():
        async for event in adapter.launch_sdk(args.prompt):
            if event.kind == EventKind.TEXT_DELTA:
                print(event.content, end="", flush=True)
            elif event.kind in (EventKind.TOOL_START, EventKind.SUBAGENT_START):
                print(f"\n[{event.kind.value}] {event.tool_name}", flush=True)
            elif event.kind == EventKind.SESSION_END:
                print(f"\n[session] {event.session_id}", flush=True)
            elif event.kind == EventKind.ERROR:
                print(f"\n[error] {event.content}", flush=True)

    asyncio.run(main())
