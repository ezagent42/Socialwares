"""{{APP_NAME}} — Socialware App 声明。

按四原语组织：Scope → Role → Flow → Commitment。
编辑此文件定义 App 的结构和关系，编辑 agent/ 下的文件定义内容。
"""

from socialwares import App

app = App("{{APP_NAME}}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Scope — 这个 App 能做什么
#    编辑 agent/scope/scope.md 描述 App 的能力边界
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app.scope(file="agent/scope/scope.md")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. Role — 谁在用这个 App
#    每个角色一个 .md 文件，放在 agent/role/ 下
#    描述这个角色是谁、能做什么
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

app.role("default", file="agent/role/default.md")
app.role("dev", file="agent/role/dev.md")
app.role("evolver", file="agent/role/evolver.md")

# 添加更多角色：
# app.role("reviewer", file="agent/role/reviewer.md")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Flow — 每个角色能做哪些操作
#    每个操作对应 agent/flow/{名称}/SKILL.md
#    SKILL.md 描述这个操作的触发条件和执行步骤
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 业务操作
app.action("check_health", role=["default"])

# 开发操作（dev 角色用于环境配置、项目导航和开发引导）
app.action("inspect", role=["dev", "evolver"])
app.action("setup_claude", role=["dev"])
app.action("dev_init", role=["dev"])
app.action("dev_iterate", role=["dev"])

# 添加更多操作：
# app.action("create_task", role=["default"])
# app.action("review_task", role=["reviewer"])

# Evolve 操作（evolver 角色专用，用于分析和改进 App）
app.action("evolve_structure_check", role=["evolver"])
app.action("evolve_api_check", role=["evolver"])
app.action("evolve_session_diagnose", role=["evolver"])
app.action("evolve_improve", role=["evolver"])
app.action("evolve_auto", role=["evolver"])

# 如果操作之间有固定的流转顺序，可以定义 Flow：
# flow = app.flow("task_lifecycle", resource="task")
# flow.states("draft", "submitted", "reviewed")
# flow.transition("draft", "submit_task", "submitted", role=["default"])
# flow.transition("submitted", "review_task", "reviewed", role=["reviewer"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. Commitment — 角色之间的协作约束
#    定义"谁做了什么之后，谁应该在什么条件下做什么"
#    只有 evolver 能看到这些约束，用于评估和改进
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# app.commitment("C1",
#     from_=("default", "submit_task"),
#     to=("reviewer", "review_task"),
#     condition="within 24h",
#     on_violation=("reviewer", "remind_review"),
# )
