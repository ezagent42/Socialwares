# 测试现状与演进计划

> 盘点当前 main 分支已有测试、缺口分析，以及测试信号如何路由到四原语改进。
>
> 理论框架见 [iteration-guide.md](iteration-guide.md) 第五章（测试与迭代）、第九章（Agent 自迭代）。
> 参考实现见 [autoservice-evolve-design.md](../../../autoservice/docs/socialware_0324/autoservice-evolve-design.md)（四层诊断 × 四原语精确映射）。
> 待设计事项见 [to-design.md](../../../autoservice/docs/socialware_0324/to-design.md)（Prompt 覆盖冲突、两条操作路径）。

---

## 目录

- [一、已有测试盘点](#一已有测试盘点)
- [二、三层测试模型覆盖状态](#二三层测试模型覆盖状态)
- [三、测试信号 → 原语改进路由表](#三测试信号--原语改进路由表)
- [四、落地计划](#四落地计划)

---

## 一、已有测试盘点

### pytest 测试（main 分支，evolve v3 已合入）

| 文件 | 测试内容 | 类型 |
|------|----------|------|
| `tests/test_deploy.py` | deploy.sh 编译管线（多平台适配、SOUL.md 合并、Skill symlink、commitment 分发） | 规范化脚本测试 |
| `tests/test_app.py` | /health + /violations API | API 测试 |
| `tests/test_create_workspace.py` | 脚手架创建 | 脚本测试 |
| `tests/test_check_structure.py` | flow.yaml ↔ SKILL.md ↔ commitment 一致性 | 规范化脚本测试 |
| `tests/test_hooks.py` | Hook 脚本生成 + JSONL 日志格式 | 规范化脚本测试 |
| `tests/test_diagnose.py` | 诊断脚本 + 日志读取 + fulfillment 计算 | Commitment 测试 |
| `tests/test_eval_script.py` | eval_cases.yaml 执行 + pass/fail 评分 | 题集测试 |
| `tests/test_violations.py` | /violations API CRUD | API 测试 |

**已知问题**（Windows 11, 2026-03-25）：deploy.sh 相关测试在 Windows 下失败（`python3` 指向 App Store 占位符 + shell 脚本无法直接执行）。CI/Linux 环境应正常通过。

### Evolver Skill 驱动的运行时测试（非 pytest）

| Evolver Skill（main 实际名称） | 测试类型 | 输入 | 运行方式 |
|-------------------------------|----------|------|----------|
| `evolve_api_check` | API 题集测试 | `eval_cases.yaml` | `run_eval.py` → HTTP 请求 → pass/fail |
| `evolve_auto` | 对话题集测试 | `conversation_tests/*.yaml` | `run_auto.py` → SDK adapter → 验证 Skill 触发 |
| `evolve_structure_check` | 结构一致性校验 | 四原语源文件 | `check_structure.py` → JSON 报告 |
| `evolve_session_diagnose` | 运行时诊断 | Hook 日志 + SDK sessions + commitment.yaml | `diagnose.py` → evolver LLM 判定 |

> **当前题集规模**：eval_cases.yaml 仅 1 条（health check），conversation_tests/default.yaml 仅 1 条（check_health）。需要在 P2 阶段逐步扩充。

---

## 二、三层测试模型覆盖状态

| 测试层 | 用途 | 状态 | 待补充 |
|--------|------|------|--------|
| **第一层：规范化脚本测试** | 验证编译管线和文件结构 | ✅ 完备（deploy + check_structure + hooks） | Windows 兼容性修复 |
| **第二层：题集测试** | 验证 Agent 行为（API + 对话） | ⚠️ 框架就绪，题集不足 | 扩充 eval_cases + conversation_tests |
| **第三层：Commitment 测试** | 运行时指标诊断 | ⚠️ 框架就绪，无真实数据 | 填充 commitment.yaml + 产生运行时数据 |

### 覆盖范围

```
当前 main 覆盖:

  agent/ 源文件 ──── deploy.sh ──── .runtime/ 产物
  (四原语)           ↑ 已测试 ↑      ↑ 已测试 ↑
       ↑                                  │
       │ evolve_structure_check           │
       │ (一致性校验)                      ▼
       │                             Agent 执行
       │                                  │
       │ evolve_improve          evolve_api_check (API)
       │ (证据驱动改进) ←──────── evolve_auto (对话)
       │         ↑               evolve_session_diagnose (运行时)
       │         │                     │
       └─────────┴─────────────────────┘
                   闭环（框架就绪，待填充真实数据）
```

---

## 三、测试信号 → 原语改进路由表

### 第一层失败路由

| 测试信号 | 工具 | 改什么 | 原语层级 |
|----------|------|--------|----------|
| SOUL.md merge 失败 | test_deploy | scope/scope.md 或 role/*.md 格式 | Scope / Role |
| Skill symlink 断裂 | test_deploy | flow.yaml 注册 vs flow/ 目录不匹配 | Flow |
| commitment 引用无效 role/action | test_check_structure | commitment.yaml 的 from/to 字段 | Commitment |
| Hook 脚本未生成 | test_hooks | deploy.sh 的 hook 生成逻辑 | 基础设施 |
| commitment 文件内容不一致 | test_deploy | 重新 deploy（.runtime/ 不应手动改） | Commitment |
| 幂等性失败 | test_deploy | deploy.sh 清理逻辑 | 基础设施 |
| Prompt 覆盖冲突（待实现） | — | 版本标记 + re-eval（参考 to-design.md §3） | 基础设施 |

### 第二层失败路由

| 测试信号 | 工具 | 改什么 | 原语层级 |
|----------|------|--------|----------|
| API 返回错误状态码 | evolve_api_check | src/app.py endpoint 实现 | Biz 层 |
| API 响应体不匹配 | evolve_api_check | endpoint 逻辑或 eval_cases.yaml 期望值 | Biz 层 / 题集 |
| Agent 没触发预期 Skill | evolve_auto | SKILL.md 的 ## Trigger 描述 | Skill 内容 |
| Agent 触发了错误 Skill | evolve_auto | Trigger 冲突或 Scope 边界 | Flow / Scope |
| Agent 未触发任何 Skill | evolve_auto | flow.yaml 未注册或 Skill 未分配给该 role | Flow |

### 第三层失败路由

| 测试信号 | 工具 | 改什么 | 原语层级 |
|----------|------|--------|----------|
| commitment VIOLATED（时间超限） | evolve_session_diagnose | 优化 Skill 执行步骤减少延迟 | Skill 内容 |
| commitment VIOLATED（顺序错误） | evolve_session_diagnose | flow.yaml 状态机 transitions | Flow |
| commitment INSUFFICIENT DATA | evolve_session_diagnose | Hook 采集覆盖不足或 App 使用量不够 | 基础设施 |
| fulfillment rate 持续低 | evolve_session_diagnose | 系统性问题 → 按第四章四层诊断 | 多层级 |
| /violations 堆积未解决 | test_violations | 缺少自动升级机制（on_violation） | Commitment |

### 路由决策流程图

```
测试失败
  │
  ├─ 第一层（编译/结构）失败
  │     ├─ deploy.sh 报错          → 修 deploy.sh 或环境
  │     ├─ 文件结构不对             → 修四原语源文件
  │     └─ 一致性校验失败           → evolve_structure_check 报告定位
  │
  ├─ 第二层（题集）失败
  │     ├─ API 测试失败             → 修 src/app.py（Biz 层）
  │     └─ 对话测试失败             → 按 iteration-guide 第四章四层诊断
  │          ① Skill Trigger → ② flow.yaml 注册 → ③ Scope 边界 → ④ Role 权限
  │
  └─ 第三层（Commitment）失败
        ├─ 单个 commitment 违规     → evolve_improve 定向修复
        └─ 系统性违规               → 整体诊断 → 可能需要改 Flow 状态机或 Scope
```

---

## 四、落地计划

### 已完成（evolve v3，已合入 main）

```
✅ 第一层增强: test_check_structure.py + test_hooks.py
✅ 第二层框架: evolve_api_check (API 题集) + evolve_auto (对话题集)
✅ 第三层框架: evolve_session_diagnose (运行时诊断) + test_violations.py
✅ Evolver 角色 + 5 个 Evolve Skill + inspect Skill
✅ Hook 系统 (log_prompt.sh + log_tool.sh)
✅ commitment.yaml schema (from/to/condition/on_violation)
✅ 多平台 deploy (Claude/Codex/Kimi)
✅ SDK adapter (claude_agent_sdk) 支持异步迭代
```

### 待建（按优先级排序）

```
优先级 1: 修复 Windows 兼容性
  · test_deploy.py: run_deploy() 用 ["bash", deploy_sh]
  · deploy.sh: python3 → python fallback

优先级 2: 扩充题集（P2 阶段同步进行）
  · 每加一个 Skill → eval_cases.yaml 加一条 API 测试
  · 每加一个 Skill → conversation_tests/ 加一条对话测试
  · 当前各 1 条 → 目标随 Skill 数量线性增长

优先级 3: 填充 commitment.yaml（P3 阶段）
  · 填入真实的质量/时间/顺序 commitment 条目
  · 这将激活 diagnose → judge → violation 完整闭环
  · 当前 commitments: {} 为空

优先级 4: Agent SDK Web 接入（iteration-guide 第八章）
  · 在现有 launch_sdk(prompt) → AsyncIterator 基础上
  · 扩展为多轮会话管理 (create_session / send_message / close_session)
  · 需解决：launch_sdk 返回原始 dict vs send_message 返回统一 AgentEvent

优先级 5: deploy 变更摘要输出
  · deploy.sh 输出 [deploy] + Skill added / ~ Scope updated 等
  · 对 Dev 的迭代可观测性（iteration-guide 第六章）

优先级 6: 渐进自治的显式标注
  · evolver Skill 中标注当前自治等级（L0/L1）
  · 随着验证通过率上升，逐步放开等级（iteration-guide 第九章 9.7）
```

### autoservice 参考架构的增强方向

> 来源：[autoservice-evolve-design.md](../../../autoservice/docs/socialware_0324/autoservice-evolve-design.md) + [to-design.md](../../../autoservice/docs/socialware_0324/to-design.md)

以下是 autoservice 设计中已详细规划、当前 main 尚未实现的增强点：

```
优先级 7: 四层诊断增强
  · evolve_session_diagnose 从单层诊断升级为 L1→L4 分层
  · L1: 数据层脚本（kb_checker 等价物）
  · L2: Prompt 质量题集
  · L3: 流程逻辑路径分析（trace_analyzer 等价物）
  · L4: 模型行为多次重复验证
  · 参考: autoservice-evolve-design.md §3

优先级 8: evaluator / evolver 角色分离
  · evaluator 只做测量（diagnose + batch-eval 两种模式）
  · evolver 只做改进（map → branch → compare → materialize）
  · 当前 main 用单一 evolver 角色同时承担两个职责
  · 参考: autoservice-evolve-design.md §4

优先级 9: 蒙特卡洛分支验证
  · evolve_improve 从直接修改 → 生成 2-3 个 delta 变体
  · evaluator batch-eval 对各分支打分
  · skill_diff 对比 → 选最优 → materialize
  · 参考: autoservice-evolve-design.md §4

优先级 10: Commitment 自动升级
  · 同类问题 3 次出现 → 自动触发增加基线测试用例
  · 升级后验证闭环：全量回归 + 通过率不降 >5%
  · 参考: autoservice-evolve-design.md §5

优先级 11: Prompt 覆盖冲突检测
  · 平台升级导致租户 .runtime/data/prompts/ 覆盖文件失效
  · 四种方案：版本标记 / 语义 diff / 分层覆盖 / 强制 re-eval
  · 多租户场景（P0+）时需要
  · 参考: to-design.md §3

优先级 12: 两条操作路径（Path A/B）测试
  · Path A（声明式配置）：验证 .runtime/data/ 修改 → deploy → 行为变化
  · Path B（技术支持）：验证 agent/ 修改 → deploy → PR → 全租户生效
  · 参考: to-design.md §2
```
