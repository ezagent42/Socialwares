"""Seed database with example Agent data."""
from __future__ import annotations

from src.db import Database

EXAMPLE_AGENT_ID = "example-cr"
EXAMPLE_USER_ID = "__system__"


async def seed_example_agent(db: Database) -> None:
    """Create the code-review-example Agent if it doesn't exist."""
    conn = await db.connect()
    try:
        # Check if already seeded
        cursor = await conn.execute("SELECT id FROM agents WHERE id = ?", (EXAMPLE_AGENT_ID,))
        if await cursor.fetchone():
            return

        # Ensure system user exists
        cursor = await conn.execute("SELECT id FROM users WHERE id = ?", (EXAMPLE_USER_ID,))
        if not await cursor.fetchone():
            await conn.execute(
                "INSERT INTO users (id, github_id, github_login, github_name) VALUES (?, ?, ?, ?)",
                (EXAMPLE_USER_ID, 0, "__system__", "System")
            )

        # === Agent ===
        await conn.execute(
            "INSERT INTO agents (id, user_id, name, description, model, is_example) VALUES (?, ?, ?, ?, ?, ?)",
            (EXAMPLE_AGENT_ID, EXAMPLE_USER_ID, "code-review-example",
             "Code review Agent — reviews pull requests, checks code quality, and provides improvement suggestions.",
             "claude", 1)
        )

        # === Scope ===
        scope_md = """# Code Review Agent

Automated code review assistant for development teams.

## Capabilities

- Review pull requests and code changes
- Check code quality (style, complexity, security)
- Detect common bugs and anti-patterns
- Suggest improvements with code examples
- Verify test coverage for changed code

## Boundaries

- Only reviews code, does not make changes directly
- Focuses on the diff/changeset, not the entire codebase
- Does not run tests or CI pipelines
- Respects team coding standards defined in the project
"""
        await conn.execute(
            "INSERT INTO scopes (id, agent_id, soul_md) VALUES (?, ?, ?)",
            ("sc-example", EXAMPLE_AGENT_ID, scope_md)
        )

        # === Roles ===
        # Role: default (reviewer)
        default_role_md = """# Code Reviewer

You are a code review agent. You review submitted code changes with a focus on quality, correctness, and maintainability.

## Identity

- Role: default
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
"""
        await conn.execute(
            "INSERT INTO roles (id, agent_id, name, soul_md) VALUES (?, ?, ?, ?)",
            ("r-default", EXAMPLE_AGENT_ID, "default", default_role_md)
        )

        # Role: senior-reviewer
        senior_role_md = """# Senior Reviewer

You are a senior code reviewer with deep expertise. You focus on architecture, design patterns, and system-level concerns beyond basic code quality.

## Identity

- Role: senior-reviewer
- Permissions: read code, post review comments, approve/request changes, escalate to tech lead

## Responsibilities

1. Review architectural decisions in the code
2. Check for scalability and performance implications
3. Evaluate error handling and edge cases
4. Assess backward compatibility
5. Mentor junior developers through review comments
"""
        await conn.execute(
            "INSERT INTO roles (id, agent_id, name, soul_md) VALUES (?, ?, ?, ?)",
            ("r-senior", EXAMPLE_AGENT_ID, "senior-reviewer", senior_role_md)
        )

        # === Skills ===
        # Skill: review_diff
        review_diff_md = """---
name: review_diff
description: "Review a code diff and provide feedback"
---

# Review Diff

## Trigger

User submits a code diff or pull request for review.
Examples: "review this PR", "check this code", "review the changes"

## Flow

1. Receive the code diff (file path, PR URL, or pasted code)
2. Analyze each changed file:
   - Security: SQL injection, XSS, secrets in code
   - Correctness: Logic errors, null checks, edge cases
   - Style: Naming conventions, code organization
   - Performance: N+1 queries, unnecessary allocations
3. Generate review with:
   - Summary: overall assessment (approve/request changes)
   - Issues: list of problems with severity (critical/warning/info)
   - Suggestions: concrete code improvements
4. Return structured review result

## API

- Read file: `GET /files/{path}`
- Submit review: `POST /reviews`
"""
        await conn.execute(
            "INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES (?, ?, ?, ?, ?)",
            ("s-review", EXAMPLE_AGENT_ID, "review_diff", "Review a code diff and provide feedback", review_diff_md)
        )

        # Skill: check_style
        check_style_md = """---
name: check_style
description: "Check code style and formatting"
---

# Check Style

## Trigger

User asks to check coding style or formatting.
Examples: "check style", "lint this code", "formatting issues?"

## Flow

1. Receive code or file path
2. Check against project conventions:
   - Indentation (tabs vs spaces)
   - Naming conventions (camelCase, snake_case)
   - Line length limits
   - Import ordering
   - Consistent bracket style
3. Report violations with line numbers
4. Suggest auto-fix where possible
"""
        await conn.execute(
            "INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES (?, ?, ?, ?, ?)",
            ("s-style", EXAMPLE_AGENT_ID, "check_style", "Check code style and formatting", check_style_md)
        )

        # Skill: check_security
        check_security_md = """---
name: check_security
description: "Scan code for security vulnerabilities"
---

# Check Security

## Trigger

User asks for security review.
Examples: "security check", "find vulnerabilities", "is this safe?"

## Flow

1. Receive code or file path
2. Scan for common vulnerabilities:
   - SQL injection
   - XSS (cross-site scripting)
   - Hardcoded secrets/credentials
   - Insecure deserialization
   - Path traversal
   - Command injection
3. Rate each finding: critical / high / medium / low
4. Provide remediation guidance with code examples
"""
        await conn.execute(
            "INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES (?, ?, ?, ?, ?)",
            ("s-security", EXAMPLE_AGENT_ID, "check_security", "Scan code for security vulnerabilities", check_security_md)
        )

        # Skill: suggest_tests
        suggest_tests_md = """---
name: suggest_tests
description: "Suggest test cases for changed code"
---

# Suggest Tests

## Trigger

User asks for test suggestions.
Examples: "what tests do I need?", "suggest tests", "test coverage?"

## Flow

1. Analyze the changed code
2. Identify untested paths:
   - New functions/methods
   - Modified logic branches
   - Edge cases (null, empty, boundary values)
   - Error handling paths
3. Generate test case descriptions with:
   - Test name
   - Input/expected output
   - Why this test matters
"""
        await conn.execute(
            "INSERT INTO skills (id, agent_id, name, description, skill_md) VALUES (?, ?, ?, ?, ?)",
            ("s-tests", EXAMPLE_AGENT_ID, "suggest_tests", "Suggest test cases for changed code", suggest_tests_md)
        )

        # === Skill-Role mappings ===
        # review_diff: both roles
        await conn.execute("INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)", ("s-review", "r-default"))
        await conn.execute("INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)", ("s-review", "r-senior"))
        # check_style: default only
        await conn.execute("INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)", ("s-style", "r-default"))
        # check_security: both roles
        await conn.execute("INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)", ("s-security", "r-default"))
        await conn.execute("INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)", ("s-security", "r-senior"))
        # suggest_tests: both roles
        await conn.execute("INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)", ("s-tests", "r-default"))
        await conn.execute("INSERT INTO skill_roles (skill_id, role_id) VALUES (?, ?)", ("s-tests", "r-senior"))

        # === Commitment ===
        commitment_yaml = """commitments:
  C1:
    from: { role: default, action: review_diff }
    to: { role: senior-reviewer, action: review_diff }
    condition: "Critical security issues must be escalated to senior reviewer within 1h"
    on_violation: null

  C2:
    from: { role: default, action: review_diff }
    to: { role: default, action: suggest_tests }
    condition: "Every review that finds bugs must include test suggestions"
    on_violation: null
"""
        await conn.execute(
            "INSERT INTO commitments (id, agent_id, commitment_yaml) VALUES (?, ?, ?)",
            ("cm-example", EXAMPLE_AGENT_ID, commitment_yaml)
        )

        await conn.commit()
    finally:
        await conn.close()
