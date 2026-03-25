# Flow State Machine + Hardcoded URLs Fix Plan

## 问题

### 1. Hardcoded URLs
SKILL.md 里写了 `curl http://localhost:8001/health`。四原语是 DSL，不应包含实现细节（端口、URL）。

受影响文件：
- `agent/flow/check_health/SKILL.md` — `curl http://localhost:8001/health`
- `agent/flow/evolve_eval/SKILL.md` — `--base-url http://localhost:8001`
- `agent/flow/evolve_eval/scripts/run_eval.py` — default `http://localhost:8001`

### 2. flow.yaml 状态机没被使用
flows 的 states + transitions 声明了但没人用（只提取 role→action 映射）。

### 3. 需要做的（B + C）
- B: deploy 注入工作流到 SOUL.md（agent 知道流程）
- C: evolve_check 验证图完整性（states 可达、无死胡同）

---

## 修改计划

### Task 1: 去掉 SKILL.md 里的硬编码 URL

**原则**：SKILL.md 是给 agent 的指令，应该引用配置而非硬编码。

**方案**：SKILL.md 用变量描述，agent 从项目配置或环境读取实际 URL。

```markdown
# Before (硬编码)
curl http://localhost:8001/health

# After (引用配置)
## API
Check the app's health endpoint. The base URL depends on your app configuration
(typically defined in src/app.py, default port 8001).
```

SKILL.md 不写具体 URL——agent 通过读 src/app.py 或项目配置知道端口。

受影响文件：
- `agent/flow/check_health/SKILL.md`
- `agent/flow/evolve_eval/SKILL.md`

脚本 `run_eval.py` 的 default 保留（它有 `--base-url` 参数让用户覆盖），但注释说明是 default。

### Task 2: flow.yaml 加 resource 字段

```yaml
flows:
  F1:
    name: task_lifecycle
    resource: task              # ← 新增：状态属于什么对象
    states: [draft, submitted, under_review, approved, closed]
    transitions:
      - { from: draft, action: submit, to: submitted, role: [default] }
      - { from: submitted, action: review, to: under_review, role: [reviewer] }
```

模板里 flows 仍然是空的（`flows: {}`），注释示例加 resource。

### Task 3: deploy.sh 注入工作流到 SOUL.md (方案 B)

deploy 读 flow.yaml 的 flows 部分 → 生成工作流文本 → 追加到 SOUL.md/AGENTS.md。

```
deploy 生成的 SOUL.md:
  [scope.md 内容]
  ---
  [role.md 内容]
  ---
  ## Workflows
  ### task_lifecycle (resource: task)
  draft → submit (default) → submitted → review (reviewer) → under_review → ...
```

只在有 flows 时生成（flows: {} 时跳过）。

修改 deploy.sh：在 merge scope + role 后，追加 flows 文本。

### Task 4: evolve_check 验证图完整性 (方案 C)

check_structure.py 新增检查：

```
## Flow State Machine Graph
For each flow:
  ✓ 所有 transition 的 from/to state 在 states 列表里？
  ✓ 所有 state 都可达？（从 states[0] 出发能到达）
  ✓ 有终止状态？（有 state 没有 outgoing transition）
  ✓ 无孤立 state？（每个 state 至少有一条 in 或 out）
  ✓ transition 的 action 有 SKILL.md？（已有检查）
  ✓ transition 的 role 存在？（已有检查）
```

### Task 5: evolve_diagnose 检查转移顺序（可选，简单版）

diagnose.py 提取事件时，如果 flow.yaml 有状态机，额外输出：

```
## Flow Transition Events
  task_lifecycle: submit → review → close (按时间顺序)
  是否符合声明的转移顺序？→ evolver 判断
```

仍然不判断——只提取顺序事实，evolver LLM 对比 flow.yaml 判断。

### Task 6: 更新文档

- flow/README.md：说明 flows 的作用（注入 SOUL.md + evolve_check 验证）
- agent/commitment/README.md：确认 commitment 和 flow transitions 的关系
- README.md：流程部分更新
- docs/guides/003：四原语 Flow 部分更新

---

## 执行顺序

```
Task 1: 去掉硬编码 URL（独立，简单）
Task 2: flow.yaml 加 resource（独立，简单）
Task 3: deploy.sh 注入工作流（依赖 Task 2）
Task 4: evolve_check 图验证（依赖 Task 2）
Task 5: diagnose 转移顺序提取（可选）
Task 6: 文档更新（依赖全部）
```

Task 1+2 并行 → Task 3+4 并行 → Task 5 → Task 6
