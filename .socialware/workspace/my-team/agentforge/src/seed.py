"""Seed database with example Agent data."""
from __future__ import annotations

from src.db import Database

EXAMPLE_AGENT_ID = "example-cr"
EXAMPLE_USER_ID = "__system__"


async def seed_example_agent(db: Database) -> None:
    conn = await db.connect()
    try:
        cursor = await conn.execute("SELECT id FROM agents WHERE id = ?", (EXAMPLE_AGENT_ID,))
        if await cursor.fetchone():
            return

        cursor = await conn.execute("SELECT id FROM users WHERE id = ?", (EXAMPLE_USER_ID,))
        if not await cursor.fetchone():
            await conn.execute(
                "INSERT INTO users (id, github_id, github_login, github_name) VALUES (?, ?, ?, ?)",
                (EXAMPLE_USER_ID, 0, "__system__", "System")
            )

        role_md = '''# Code Reviewer

You are a code review agent. You review submitted code changes with a focus on quality, correctness, and maintainability.

## Identity

- Role: Code Reviewer
- Permissions: read code, post review comments, approve/request changes

## Responsibilities

1. Read the submitted code diff
2. Check for bugs, security issues, and anti-patterns
3. Verify coding style consistency
4. Suggest improvements with concrete examples
5. Approve or request changes with clear reasoning

## Tone

- Constructive and specific — always explain WHY something is an issue
- Provide code examples for suggested fixes
- Acknowledge good patterns when you see them
- Prioritize: security > correctness > performance > style
'''

        await conn.execute(
            "INSERT INTO agents (id, user_id, name, description, role_md, is_example) VALUES (?, ?, ?, ?, ?, ?)",
            (EXAMPLE_AGENT_ID, EXAMPLE_USER_ID, "code-review-example",
             "Code review Agent — reviews pull requests, checks code quality, and provides improvement suggestions.",
             role_md, 1)
        )

        skills = [
            ("s-review", "review_diff", "Review a code diff and provide feedback",
             "---\\nname: review_diff\\ndescription: \"Review a code diff\"\\n---\\n\\n# Review Diff\\n\\n## Trigger\\nUser submits a code diff or PR.\\n\\n## Flow\\n1. Analyze changed files for security, correctness, style, performance\\n2. Generate review with severity ratings\\n3. Suggest concrete fixes"),
            ("s-security", "check_security", "Scan code for security vulnerabilities",
             "---\\nname: check_security\\ndescription: \"Security scan\"\\n---\\n\\n# Check Security\\n\\n## Trigger\\nUser asks for security review.\\n\\n## Flow\\n1. Scan for SQL injection, XSS, hardcoded secrets, path traversal\\n2. Rate each finding critical/high/medium/low\\n3. Provide remediation guidance"),
            ("s-tests", "suggest_tests", "Suggest test cases for changed code",
             "---\\nname: suggest_tests\\ndescription: \"Test suggestions\"\\n---\\n\\n# Suggest Tests\\n\\n## Trigger\\nUser asks for test suggestions.\\n\\n## Flow\\n1. Identify untested code paths\\n2. Generate test descriptions with input/output\\n3. Explain why each test matters"),
            ("s-style", "check_style", "Check code style and formatting",
             "---\\nname: check_style\\ndescription: \"Style check\"\\n---\\n\\n# Check Style\\n\\n## Trigger\\nUser asks to check coding style.\\n\\n## Flow\\n1. Check naming, indentation, imports, line length\\n2. Report violations with line numbers\\n3. Suggest fixes"),
        ]

        for sid, name, desc, skill_md in skills:
            # Unescape the skill_md
            actual_md = skill_md.replace("\\n", "\n").replace('\\"', '"')
            await conn.execute(
                "INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES (?, ?, ?, ?, ?)",
                (sid, EXAMPLE_AGENT_ID, name, desc, actual_md)
            )

        await conn.commit()
    finally:
        await conn.close()
