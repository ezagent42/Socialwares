"""{{APP_NAME}} — Socialware App declaration.

Organized by four primitives: Scope -> Role -> Flow -> Commitment.
Edit this file to define the App's structure and relationships; edit files under agent/ to define content.
"""

from socialwares import App

app = App("{{APP_NAME}}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Scope — What this App can do
#    Edit agent/scope/scope.md to describe the App's capability boundaries
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app.scope(file="agent/scope/scope.md")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Role — Who uses this App
#    One .md file per role, placed under agent/role/
#    Describes who this role is and what it can do
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app.role("default", file="agent/role/default.md")
app.role("dev", file="agent/role/dev.md")
app.role("evolver", file="agent/role/evolver.md")

# Add more roles:
# app.role("reviewer", file="agent/role/reviewer.md")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Flow — What actions each role can perform
#    Each action corresponds to agent/flow/{name}/SKILL.md
#    SKILL.md describes the trigger conditions and execution steps for this action
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Business actions
app.action("check_health", role=["default"])

# Development actions (dev role for environment setup, project navigation, and development guidance)
app.action("inspect", role=["dev", "evolver"])
app.action("setup_claude", role=["dev"])
app.action("dev_define", role=["dev"])
app.action("dev_build", role=["dev"])
app.action("dev_release", role=["dev"])

# Add more actions:
# app.action("create_task", role=["default"])
# app.action("review_task", role=["reviewer"])

# Evolve actions (exclusive to the evolver role, for analyzing and improving the App)
app.action("evolve_structure_check", role=["evolver"])
app.action("evolve_api_check", role=["evolver"])
app.action("evolve_session_diagnose", role=["evolver"])
app.action("evolve_improve", role=["evolver"])
app.action("evolve_auto", role=["evolver"])

# If actions have a fixed transition order, you can define a Flow:
# flow = app.flow("task_lifecycle", resource="task")
# flow.states("draft", "submitted", "reviewed")
# flow.transition("draft", "submit_task", "submitted", role=["default"])
# flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Commitment — Collaboration constraints between roles
#    Defines "after who does what, who should do what under what conditions"
#    Only the evolver can see these constraints, used for evaluation and improvement
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# app.commitment("C1",
#     from_=("default", "submit_task"),
#     to=("reviewer", "review_task"),
#     condition="within 24h",
#     on_violation=("reviewer", "remind_review"),
# )
