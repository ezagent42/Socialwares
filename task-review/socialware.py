"""task-review — Socialware App 声明。"""

from socialwares import App

app = App("task-review", description="Task review workflow")

# ── 内容引用 ──

app.scope(file="agent/scope/scope.md")
app.role("default", file="agent/role/default.md")
app.role("reviewer", "You review and approve tasks.")
app.role("evolver", file="agent/role/evolver.md")

# ── Action 注册 ──
# action 名 = agent/flow/ 下的目录名

app.action("check_health", role=["default", "reviewer"])
app.action("create_task", role=["default"])
app.action("list_tasks", role=["default", "reviewer"])
app.action("review_task", role=["reviewer"])

app.action("evolve_structure_check", role=["evolver"])
app.action("evolve_api_check", role=["evolver"])
app.action("evolve_session_diagnose", role=["evolver"])
app.action("evolve_improve", role=["evolver"])
app.action("evolve_auto", role=["evolver"])


# ── 状态机（按需添加）──

flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed", "closed")
flow.transition("draft", "submit_task", "submitted", role=["default"])
flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])
flow.transition("reviewed", "close_task", "closed", role=["default"])

# ── 约束（按需添加）──
app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
    on_violation=("reviewer", "remind_review"),
)