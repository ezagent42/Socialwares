---
name: code_review
description: "读取指定文件或目录，检查安全漏洞、代码规范和质量问题，输出结构化审查报告"
---

# Code Review

读取用户指定的源代码文件，执行全面的代码审查并生成结构化报告。

## Trigger

User says "review this code", "review file", "代码审查", "帮我review", "检查代码", etc.

## Flow

1. Ask the user which files or directories to review (if not already specified)
2. Read all specified files completely — never truncate
3. For each file, analyze across five dimensions:
   - **Security**: OWASP Top 10, hardcoded secrets, insecure patterns
   - **Correctness**: Logic errors, edge cases, error handling
   - **Maintainability**: Naming, duplication, complexity, coupling
   - **Performance**: N+1 queries, unnecessary work, missing optimization
   - **Style**: Consistency, idiomatic patterns, documentation
4. Assign severity to each issue: CRITICAL / HIGH / MEDIUM / LOW / INFO
5. Generate structured Markdown report with:
   - Per-issue details (file, line, category, description, suggestion)
   - Summary table (issue counts by severity)
   - Overall assessment and recommended priority actions
6. If no issues found, confirm the code looks good with a brief explanation

## Constraints

- Read-only: never modify source files
- Always read files completely before reviewing
- Do not review generated files (.runtime/, node_modules/, __pycache__/)
- Output in the user's language (default: zh-CN)
