---
name: dev_define
description: "Define or redefine four primitives — the core of socialware development"
---

# Define Four Primitives

**Developing a Socialware = Defining four primitives.** Humans make decisions (define what), Agent executes automatically (writes files, registers, compiles).

## Trigger

User says "define", "init", "initialize", "redefine", "modify primitives", "redefine" etc.

## Flow

### Step 0: Assess Current State

First read the current `socialware.py` and `agent/` directory to determine:
- **New project** (only template defaults) → guide from scratch
- **Existing definitions** (already has business roles/actions) → show current definitions, ask user which part to modify

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
cat socialware.py
ls agent/role/ agent/scope/ agent/flow/
```

If definitions already exist, show a summary: "Currently there are X roles, Y actions, Z transitions, and W commitments. Which part do you want to modify? Or redefine everything from scratch?"

### Step 1: Scope — "What can this App do?"

1. Ask user: "What does this App do? What are the main features? And what does it NOT do?"
2. Based on response, write/update `agent/scope/scope.md` with exactly two sections: `## Capabilities` and `## Boundaries`. Do NOT add any other sections.
3. Show the result, confirm with user
4. See `references/four-primitives-guide.md` for scope template

### Step 2: Role — "Who uses this App?"

1. Ask user: "What roles will use this App? What are each role's responsibilities?"
2. For each role:
   - Create/update `agent/role/{name}.md`
   - Register in `socialware.py`: `app.role("name", file="agent/role/name.md")`
3. Note: default, dev, evolver are built-in roles and do not need to be defined by the user

### Step 3: Flow — "What actions can each role perform?"

1. Ask user: "What actions can each role perform?"
2. For each action:
   - Create directory: `agent/flow/{action}/` with `scripts/` and `references/` subdirs
   - Create `agent/flow/{action}/SKILL.md` with trigger + flow
   - Register in `socialware.py`: `app.action("name", role=[...])`
3. **Guide understanding of transitions**: Ask "Is there a fixed order between these actions? For example: a task must first be created, then submitted, then reviewed — you can't skip a step."
   - Use a relatable analogy: "It's like cooking — you wash the vegetables first, then chop them, then stir-fry. You can't stir-fry unwashed vegetables."
   - If yes, help define:
     ```python
     flow = app.flow("task_lifecycle", resource="task")
     flow.states("draft", "submitted", "reviewed")  # stages a task goes through
     flow.transition("draft", "submit_task", "submitted", role=["default"])
     # meaning: when a task is in draft state, default role executes submit_task, task becomes submitted
     ```
   - If confused: "A state is what stage the task is currently in. A transition is who can push it to the next stage. Actions without transitions (like viewing a list) can be used anytime."
   - If no fixed order: skip, all actions are direct actions
4. SKILL.md only needs the basic trigger + flow. Detailed authoring can use skill-creator (obtained via "setup claude")

### Step 4: Commitment — "How do roles collaborate?"

**This is the hardest part to understand and requires patient guidance.**

1. First determine if it's needed:
   - "Are there scenarios in the App that require multi-person collaboration? For example, one person submits something, and another person needs to handle it within a certain timeframe?"
   - If only one role or no time constraints: skip
   - If yes: continue

2. Guide with concrete scenarios:
   - "Imagine: {Role A} performs {Action A}. What do you expect {Role B} to do, and under what conditions, with {Action B}?"
   - Example: "Like food delivery: after a customer places an order (from), the rider should pick up the food within 30 minutes (to + condition). If it times out, the system reminds the rider (on_violation)."
   - Explain the purpose: "Once these rules are defined, the evolver role will automatically detect whether they are being followed."

3. For each commitment:
   ```python
   app.commitment("C1",
       from_=("default", "submit_task"),     # who did what
       to=("reviewer", "review_task"),        # who should do what
       condition="within 24h",                # under what condition
       on_violation=("reviewer", "remind_review"),  # what happens if violated
   )
   ```

4. Confirm with a plain-language translation: "After default submits a task, reviewer should review it within 24 hours. If not, remind_review is triggered."

### Step 5: Deploy + Verify

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
socialwares deploy
```

Show compile result (roles, skills per role), confirm everything correct.

Then say: "Four primitives definition complete. You can now say **build** to start developing frontend and backend (TDD: write tests → implement → verify)."

## Critical Rules

1. **Strictly step-by-step**: Only guide one primitive at a time (Scope → Role → Flow → Commitment). After completing one, show the result and wait for the user to confirm "OK" / "continue" before moving to the next. **Never ask all questions at once.**
2. **Look before you change**: If the project already has definitions, show the current state first, then ask which part to modify
3. **Strictly follow the template**: Only use fields defined in `references/four-primitives-guide.md`. Do not improvise or add sections/fields not in the template
4. **Use the user's language**: If the user speaks Chinese, use Chinese; if English, use English
5. **After deploy, guide to build, not default/evolver**: After define is complete, frontend and backend are not yet implemented. The next step should be "You can now say 'build' to start developing frontend and backend", not guiding to `socialwares start --role default`
