"""Export agent — dispatch to format-specific adapters."""
from __future__ import annotations
import tempfile
import zipfile
from pathlib import Path
from src.db import Database
from src.adapters.gitagent import GitAgentAdapter
from src.adapters.claude_code import ClaudeCodeAdapter
from src.adapters.codex import CodexAdapter
from src.adapters.cursor import CursorAdapter
from src.adapters.socialwares import SocialwaresAdapter

ADAPTERS = {
    "gitagent": GitAgentAdapter,
    "claude-code": ClaudeCodeAdapter,
    "codex": CodexAdapter,
    "cursor": CursorAdapter,
    "socialwares": SocialwaresAdapter,
}

FORMATS = list(ADAPTERS.keys())


async def export_agent(db: Database, agent_id: str, output_dir: Path, format: str = "gitagent") -> dict:
    adapter = ADAPTERS.get(format)
    if not adapter:
        raise ValueError(f"Unknown format: {format}. Available: {', '.join(FORMATS)}")
    return await adapter.export(db, agent_id, output_dir)


async def export_agent_zip(db: Database, agent_id: str, format: str = "gitagent") -> tuple[Path, str]:
    tmp_dir = Path(tempfile.mkdtemp())
    result = await export_agent(db, agent_id, tmp_dir / "export", format=format)
    agent_name = result["agent_name"]
    zip_path = tmp_dir / f"{agent_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        export_root = tmp_dir / "export"
        for file_path in export_root.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, str(file_path.relative_to(export_root)))
    return zip_path, agent_name
