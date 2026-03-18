"""Configuration loader for Socialware skills.

Loads config.yaml from each skill directory. Follows AutoService pattern.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_skill_config(skill_dir: str | Path) -> dict[str, Any]:
    """Load config.yaml from a skill directory.

    Args:
        skill_dir: Path to the skill directory containing config.yaml

    Returns:
        Parsed config dict. Empty dict if config.yaml not found.
    """
    config_path = Path(skill_dir) / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def get_api_url(config: dict[str, Any]) -> str:
    """Extract API base URL from skill config."""
    return config.get("api_url", "http://localhost:8000")
