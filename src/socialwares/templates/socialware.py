"""{{APP_NAME}} — Socialware App 声明。"""

from socialwares import App

app = App("{{APP_NAME}}")

# ── 内容引用 ──

app.scope(file="agent/scope/scope.md")
app.role("default", file="agent/role/default.md")
app.role("evolver", file="agent/role/evolver.md")

# ── Action 注册 ──
# action 名 = agent/flow/ 下的目录名

app.action("check_health", role=["default"])

# evolve skill（和业务 skill 一样注册）
app.action("evolve_structure_check", role=["evolver"])
app.action("evolve_api_check", role=["evolver"])
app.action("evolve_session_diagnose", role=["evolver"])
app.action("evolve_improve", role=["evolver"])
app.action("evolve_auto", role=["evolver"])

# ── 状态机（按需添加）──

# flow = app.flow("lifecycle", resource="task")
# flow.states("draft", "submitted", "reviewed")
# flow.transition("draft", "submit", "submitted", role=["default"])

# ── 约束（按需添加）──

# app.commitment("C1",
#     from_=("default", "submit"),
#     to=("reviewer", "review"),
#     condition="within 24h",
# )
