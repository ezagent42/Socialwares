import pytest
from src.claude_adapter import AGENT_TOOLS


def test_agent_tools_defined():
    """All 10 CRUD tools should be defined with name, description, input_schema."""
    assert len(AGENT_TOOLS) == 10
    names = {t["name"] for t in AGENT_TOOLS}
    expected = {
        "list_agents", "create_agent", "get_agent", "delete_agent",
        "create_skill", "list_skills", "delete_skill",
        "export_agent", "search_skills", "import_agent",
    }
    assert names == expected
    for tool in AGENT_TOOLS:
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
