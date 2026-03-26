# 开发指南

## 1. 整体机制

### 模板 → Workspace → Runtime

```
Socialwares (模板仓库)
  │
  ├── agent/          ← 四原语定义 + 适配器 + 部署脚本
  ├── src/            ← 应用模板代码
  └── scripts/        ← create-my-socialware.py
        │
        │  make create ROOM=team APP=myapp
        ▼
.socialware/workspace/team/myapp/ (Workspace)
  │
  ├── agent/          ← 四原语（从模板复制，可自定义）
  ├── src/            ← 应用代码（从模板复制，自行开发）
  ├── Makefile        ← 从 Makefile.template 复制
  └── pyproject.toml  ← 独立 Python 环境
        │
        │  make deploy
        ▼
.runtime/ (Runtime，编译产物)
  ├── agents/{role}/  ← 每个角色的 SOUL.md + skills symlinks + hooks
  └── data/           ← prompts/ sessions/ evolve/
```

### 开发自己的软件

1. `make create` 创建 workspace
2. 在 `src/` 下写后端代码（FastAPI endpoints）
3. 在 `agent/flow/` 下写 SKILL.md（agent 怎么调用你的 API）
4. 在 `agent/flow/flow.yaml` 注册 action + 分配 role
5. `make deploy` 编译 → `make start` 启动 agent

### 改进模板

1. 在模板根目录修改 `agent/` 下的脚本、适配器、部署逻辑
2. workspace 通过 `make sync` 同步模板的基础设施（脚本、适配器、Makefile）
3. SKILL.md 和 references/ 是用户可自定义的，sync 不覆盖

---

## 2. 渐进式开发流程

### 四原语

| 原语 | 目录 | 回答什么 | 对应软件层 |
|------|------|---------|-----------|
| **Role** | `agent/role/*.md` | 谁？ | 前端：用户角色/权限；后端：RBAC |
| **Scope** | `agent/scope/scope.md` | 在哪里？ | 前端：功能边界/UI 可见性；后端：API 范围 |
| **Commitment** | `agent/commitment/commitment.yaml` | 什么标准？ | 前端：约束提示；后端：校验逻辑 |
| **Flow** | `agent/flow/flow.yaml` + `SKILL.md` | 怎么做？ | 前端：页面/交互流程；后端：API endpoints + 状态机 |

### 为什么四原语映射到前后端

```
四原语（DSL）        Agent 行为          软件实现
─────────────        ──────────          ────────
Role    ─────────→   SOUL.md 角色身份  → RBAC + 权限 API
Scope   ─────────→   SOUL.md 能力边界  → API scope + UI 可见性
Flow    ─────────→   SKILL.md 操作指引  → API endpoints + 状态机
Commitment ──────→   评估标准（仅 evolver 可见）→ 校验逻辑
```

四原语是 agent 的 DSL（声明式语言），deploy 编译为 SOUL.md（agent 看到的指令）。agent 通过 SKILL.md 知道"怎么调用 API"，所以每个 SKILL.md 对应一个后端 endpoint。

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
    Note right of Commitment: 调整 condition / 加 on_violation
    Dev->>Scope: 3. 范围清晰吗？声明和实际一致吗？
    Note right of Scope: 更新 scope.md
    Dev->>Role: 4. 需要新角色吗？
    Note right of Role: 添加 role/*.md + flow.yaml 分配
```

**Commitment 的核心作用**：它是四原语之间的"质量胶水"。Commitment 不强制执行，而是定义评估标准——evolver 读取 commitment.yaml，对比实际行为数据，判断是否达标，然后反推应该改进哪个原语。

### 一般开发流程

```mermaid
sequenceDiagram
    participant Dev as 开发者
    participant App as src/app.py
    participant Agent as agent/
    participant Deploy as make deploy
    participant Evolver as evolver

    Dev->>App: 1. 写后端 API (FastAPI)
    Dev->>Agent: 2. 写 SKILL.md + flow.yaml
    Dev->>Deploy: 3. make deploy
    Deploy-->>Agent: 编译 → .runtime/
    Dev->>Agent: 4. make start ROLE=default
    Note right of Dev: 使用 agent，产生对话数据
    Dev->>Evolver: 5. make start ROLE=evolver
    Evolver->>Evolver: structure_check → api_check → session_diagnose → improve
    Evolver-->>Dev: 改进建议（原语 + 后端）
    Dev->>App: 6. 根据建议修改代码
    Dev->>Deploy: 7. make deploy → 下一轮
```

---

## 3. Evolver 的作用

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
| `agent/commitment/commitment.yaml` | 评估标准 | `diagnose.py` 提取事件，evolver 判断 |

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

    Note over Dev: 根据建议修改 → make deploy → 下一轮
```

### 收到 improve 建议后的开发流程

```mermaid
sequenceDiagram
    participant Evolver as evolver
    participant Dev as 开发者
    participant Code as 代码修改
    participant Deploy as make deploy
    participant Verify as 验证

    Evolver-->>Dev: 建议: "create_task SKILL.md 缺 JSON 格式 + 后端需加 POST /tasks"
    Dev->>Code: 1. 修改 agent/flow/create_task/SKILL.md
    Dev->>Code: 2. 实现 src/app.py POST /tasks endpoint
    Dev->>Code: 3. 添加 eval_cases.yaml 测试用例
    Dev->>Code: 4. 添加 conversation_tests 测试用例
    Dev->>Deploy: 5. make deploy
    Dev->>Verify: 6. make start ROLE=evolver → "evaluate"
    Verify-->>Dev: API 通过率提升？
    Dev->>Verify: 7. "auto-test"
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
