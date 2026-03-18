"""Base adapter interface for multi-platform agent launching.

Each adapter reads a GitAgent directory (agent.yaml + SOUL.md + skills/)
and launches the agent using the platform's SDK.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentConfig:
    """Parsed agent configuration from GitAgent format."""

    name: str
    version: str
    description: str
    model_preferred: str
    model_fallback: list[str] = field(default_factory=list)
    soul: str = ""
    rules: str = ""
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    max_turns: int = 100
    timeout: int = 3600

    @classmethod
    def from_dir(cls, agent_dir: str | Path) -> AgentConfig:
        """Load agent config from a GitAgent directory."""
        agent_dir = Path(agent_dir)
        with open(agent_dir / "agent.yaml") as f:
            raw = yaml.safe_load(f)

        soul = ""
        soul_path = agent_dir / "SOUL.md"
        if soul_path.exists():
            soul = soul_path.read_text()

        rules = ""
        rules_path = agent_dir / "RULES.md"
        if rules_path.exists():
            rules = rules_path.read_text()

        model = raw.get("model", {})
        runtime = raw.get("runtime", {})

        return cls(
            name=raw["name"],
            version=raw["version"],
            description=raw["description"],
            model_preferred=model.get("preferred", "claude-sonnet-4-6"),
            model_fallback=model.get("fallback", []),
            soul=soul,
            rules=rules,
            skills=raw.get("skills", []),
            tools=raw.get("tools", []),
            max_turns=runtime.get("max_turns", 100),
            timeout=runtime.get("timeout", 3600),
        )


class BaseAdapter(abc.ABC):
    """Abstract base class for agent SDK adapters."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    @abc.abstractmethod
    def build_system_prompt(self) -> str:
        """Build the system prompt from SOUL + RULES + SKILLs."""
        ...

    @abc.abstractmethod
    def launch(self) -> None:
        """Launch the agent using the platform SDK."""
        ...

    @abc.abstractmethod
    def launch_headless(self, task: str) -> Any:
        """Launch the agent headlessly with a specific task."""
        ...
