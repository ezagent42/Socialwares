"""Parse structured blocks from Agent's streaming response."""
from __future__ import annotations

import json
import re


def parse_agent_response(text: str) -> tuple[str, dict | None]:
    """Extract json:structured block from Agent response.

    Returns (clean_text, structured_data_or_none).
    """
    pattern = r'```json:structured\n(.*?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return text, None

    try:
        structured = json.loads(match.group(1))
    except json.JSONDecodeError:
        return text, None

    clean = text[:match.start()].rstrip() + text[match.end():].lstrip()
    return clean.strip(), structured
