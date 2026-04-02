---
name: find_skill
description: "Search and discover existing skills from local DB and built-in templates"
---

# Find Skill

## Trigger

User asks to find, search, or discover skills.

Examples:
- "Find skills about code review"
- "Search for security skills"
- "/find-skill"

## Flow

1. Accept search keyword from user
2. Search local DB skills and built-in template skills
3. Present results with name, source, and description
4. User selects a skill to view details
5. Optionally add selected skill to an Agent via `/add-skill`

## How to Execute

Use the find_skill module:

```bash
uv run python -c "
import asyncio
from src.db import Database
from src.crud.find_skill import search_skills
db = Database('$DB_PATH')
asyncio.run(db.init())
results = asyncio.run(search_skills(db, '$USER_ID', '$QUERY'))
import json; print(json.dumps(results, ensure_ascii=False, indent=2))
"
```

## Structured Response

- type: "skill"
- action: "listed"
- data: { query, results: [{ name, description, source, skill_md }] }
