# 开发指南

## 1. 整体机制

### 框架 → 项目 → Runtime

```
pip install socialwares (框架 pip 包)
  │
  │  socialwares new task-review
  ▼
task-review/ (用户项目)
  │
  ├── socialware.py   ← 关系定义（action→role, 状态机, commitment）
  ├── agent/          ← 内容文件（role/*.md, scope/scope.md, flow/*/SKILL.md）
  ├── src/api.py      ← FastAPI 后端
  ├── app/            ← 前端 UI
  └── pyproject.toml  ← 项目配置 [tool.socialwares]
        │
        │  socialwares deploy
        ▼
.runtime/ (Runtime，编译产物)
  ├── agents/{role}/  ← 每个角色的 SOUL.md + skills symlinks + hooks
  ├── flow.yaml       ← 从 socialware.py 生成
  ├── commitment.yaml ← 从 socialware.py 生成
  └── data/           ← prompts/ sessions/ evolve/
```

### 开发自己的软件

1. `socialwares new my-app` 创建项目
2. 在 `agent/` 下写内容文件（role、scope、flow SKILL.md）
3. 在 `socialware.py` 定义关系（action→role 映射、状态机、commitment）
4. 在 `src/` 下写后端代码（FastAPI endpoints）
5. `socialwares deploy` 编译 → `socialwares start --role default` 启动 agent

### 升级框架

```bash
pip install --upgrade socialwares
```

框架升级不影响用户项目内容（`socialware.py`、`agent/`、`src/` 都属于用户）。

---

## 2. 渐进式开发流程

### 四原语

| 原语 | 定义位置 | 内容位置 | 回答什么 | 对应软件层 |
|------|---------|---------|---------|-----------|
| **Role** | `socialware.py` `app.role(...)` | `agent/role/*.md` | 谁？ | 前端：用户角色/权限；后端：RBAC |
| **Scope** | `socialware.py` `app.scope(...)` | `agent/scope/scope.md` | 在哪里？ | 前端：功能边界/UI 可见性；后端：API 范围 |
| **Commitment** | `socialware.py` `app.commitment(...)` | 无（编译为 .runtime/commitment.yaml） | 什么标准？ | 前端：约束提示；后端：校验逻辑 |
| **Flow** | `socialware.py` `app.action(...)` / `app.flow(...)` | `agent/flow/*/SKILL.md` | 怎么做？ | 前端：页面/交互流程；后端：API endpoints + 状态机 |

### 为什么四原语映射到前后端

```
四原语（DSL）             Agent 行为           软件实现
─────────────            ──────────           ────────
Role    ──────────→   SOUL.md 角色身份     → RBAC + 权限 API
Scope   ──────────→   SOUL.md 能力边界     → API scope + UI 可见性
Flow    ──────────→   SKILL.md 操作指引    → API endpoints + 状态机
Commitment ───────→   评估标准（仅 evolver 可见）→ 校验逻辑
```

四原语分为两个层面：
- **关系定义** 在 `socialware.py`（声明式 Python API）
- **内容定义** 在 `agent/` 下的文件

`socialwares deploy` 将两者编译为 `.runtime/`（agent 看到的指令）。agent 通过 SKILL.md 知道"怎么调用 API"，所以每个 SKILL.md 对应一个后端 endpoint。

### 进化顺序：Flow → Commitment → Scope → Role

```mermaid
sequenceDiagram
    participant Dev as 开发者
    participant Flow as Flow (功能)
    participant Commitment as Commitment (标准)
    participant Scope as Scope (边界)
    participant Role as Role (角色)

    Dev->>Flow: 1. 功能完善吗？缺哪些 skill？
    Note right of Flow: 加 SKILL.md + 实现 API endpoint
    Dev->>Commitment: 2. 约束合理吗？需要什么校验？
    Note right of Commitment: 在 socialware.py 调整 condition / 加 on_violation
    Dev->>Scope: 3. 范围清晰吗？声明和实际一致吗？
    Note right of Scope: 更新 agent/scope/scope.md
    Dev->>Role: 4. 需要新角色吗？
    Note right of Role: 添加 agent/role/*.md + socialware.py 注册
```

**Commitment 的核心作用**：它是四原语之间的"质量胶水"。Commitment 不强制执行，而是定义评估标准——evolver 读取 `.runtime/commitment.yaml`，对比实际行为数据，判断是否达标，然后反推应该改进哪个原语。

### 一般开发流程

```mermaid
sequenceDiagram
    participant Dev as 开发者
    participant App as src/api.py
    participant Agent as socialware.py + agent/
    participant Deploy as socialwares deploy
    participant Evolver as evolver

    Dev->>App: 1. 写后端 API (FastAPI)
    Dev->>Agent: 2. 写 SKILL.md + socialware.py 注册 action
    Dev->>Deploy: 3. socialwares deploy
    Deploy-->>Agent: 编译 → .runtime/
    Dev->>Agent: 4. socialwares start --role default
    Note right of Dev: 使用 agent，产生对话数据
    Dev->>Evolver: 5. socialwares start --role evolver
    Evolver->>Evolver: structure_check → api_check → session_diagnose → improve
    Evolver-->>Dev: 改进建议（原语 + 后端）
    Dev->>App: 6. 根据建议修改代码
    Dev->>Deploy: 7. socialwares deploy → 下一轮
```

---

## 3. Evolver 的作用

Evolver 是普通角色，与业务角色使用完全相同的 skill 结构和编译逻辑。

### 命令一览

| 命令 | Skill | 做什么 | 需要 App 运行？ |
|------|-------|--------|---------------|
| `"check structure"` | `evolve_structure_check` | 检查四原语结构一致性 + 流图完整性 | 否 |
| `"evaluate"` | `evolve_api_check` | 运行 eval_cases.yaml HTTP 测试 | 是 |
| `"diagnose"` | `evolve_session_diagnose` | 从对话日志提取 commitment 事件 + 流转移事件 | 否 |
| `"improve"` | `evolve_improve` | 基于证据提出改进建议 + 应用修改 | 否 |
| `"auto-test"` | `evolve_auto` | 通过 SDK 运行对话测试用例 | 是 |

### 需要提供的文件

| 文件 | 用途 | 自动化测试 |
|------|------|-----------|
| `agent/flow/evolve_api_check/eval_cases.yaml` | HTTP API 测试用例 | `run_eval.py` |
| `agent/flow/evolve_auto/conversation_tests/*.yaml` | 对话测试用例（expected_skill + expected_contains + expected_not_contains） | `run_auto.py` |
| `socialware.py` 中的 `app.commitment(...)` | 评估标准 | `diagnose.py` 提取事件，evolver 判断 |

### Evolver 生命周期

```mermaid
sequenceDiagram
    participant Dev as 开发者
    participant SC as structure_check
    participant AC as api_check
    participant SD as session_diagnose
    participant Imp as improve
    participant AT as auto-test

    Dev->>SC: 1. "check structure"
    SC-->>Dev: 结构问题报告（缺 SKILL.md、角色不匹配、图不完整）
    Note right of Dev: 先修结构问题

    Dev->>AC: 2. "evaluate" (App 运行中)
    AC-->>Dev: API 通过率 (e.g. 3/4 = 75%)

    Dev->>SD: 3. "diagnose"
    SD-->>Dev: commitment 事件提取 + 流转移事件
    Note right of SD: evolver 判断 FULFILLED/VIOLATED
    SD->>SD: save_violation.py (如有违反)

    Dev->>Imp: 4. "improve"
    Imp-->>Dev: 建议：修改哪个原语 + 后端代码
    Note right of Imp: 思考顺序: Flow→Commitment→Scope→Role
    Imp->>Imp: save_report.py (记录改进)

    Dev->>AT: 5. "auto-test" (可选)
    AT-->>Dev: 对话测试通过率 + 失败根因分析

    Note over Dev: 根据建议修改 → socialwares deploy → 下一轮
```

### 收到 improve 建议后的开发流程

```mermaid
sequenceDiagram
    participant Evolver as evolver
    participant Dev as 开发者
    participant Code as 代码修改
    participant Deploy as socialwares deploy
    participant Verify as 验证

    Evolver-->>Dev: 建议: "create_task SKILL.md 缺 JSON 格式 + 后端需加 POST /tasks"
    Dev->>Code: 1. 修改 agent/flow/create_task/SKILL.md
    Dev->>Code: 2. 实现 src/api.py POST /tasks endpoint
    Dev->>Code: 3. 在 socialware.py 确认 action 注册
    Dev->>Code: 4. 添加 eval_cases.yaml 测试用例
    Dev->>Code: 5. 添加 conversation_tests 测试用例
    Dev->>Deploy: 6. socialwares deploy
    Dev->>Verify: 7. socialwares start --role evolver → "evaluate"
    Verify-->>Dev: API 通过率提升？
    Dev->>Verify: 8. "auto-test"
    Verify-->>Dev: 对话测试通过率提升？
    alt 通过率满意
        Dev->>Dev: 进入下一个功能
    else 仍有问题
        Dev->>Verify: "diagnose" → "improve" → 继续循环
    end
```

**关键原则**：
- 每次只改一个原语，测量改进效果后再改下一个
- 原语改动通常伴随后端代码改动（SKILL.md 加了新操作 → 后端要有对应 API）
- 用 eval_cases.yaml 和 conversation_tests 固化测试，防止回归
- `save_report.py` 记录每次改进，形成审计轨迹
- 关系定义（action→role, 状态机, commitment）在 `socialware.py`，内容定义在 `agent/` 文件
