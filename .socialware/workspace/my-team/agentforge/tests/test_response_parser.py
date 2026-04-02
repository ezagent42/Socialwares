from src.response_parser import parse_agent_response


def test_extract_structured():
    text = 'Agent created successfully!\n\n```json:structured\n{"type": "agent", "action": "created", "data": {"id": "abc"}}\n```'
    clean, structured = parse_agent_response(text)
    assert clean == "Agent created successfully!"
    assert structured["type"] == "agent"
    assert structured["action"] == "created"
    assert structured["data"]["id"] == "abc"


def test_no_structured():
    text = "Just plain text response."
    clean, structured = parse_agent_response(text)
    assert clean == text
    assert structured is None


def test_invalid_json():
    text = '```json:structured\n{bad json}\n```'
    clean, structured = parse_agent_response(text)
    assert structured is None


def test_text_before_and_after():
    text = 'Before\n\n```json:structured\n{"ok": true}\n```\n\nAfter'
    clean, structured = parse_agent_response(text)
    assert "Before" in clean
    assert "After" in clean
    assert structured == {"ok": True}
