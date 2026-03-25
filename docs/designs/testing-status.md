# 测试现状与演进计划

> 盘点当前已有测试、evolve-v2 分支新增测试、缺口分析，以及测试信号如何路由到四原语改进。
>
> 理论框架见 [iteration-guide.md](iteration-guide.md) 第五章（测试与迭代）、第九章（Agent 自迭代）。
> 参考实现见 [autoservice-evolve-design.md](../../../autoservice/docs/socialware_0324/autoservice-evolve-design.md)（四层诊断 × 四原语精确映射）。

---

## 目录

- [一、已有测试盘点](#一已有测试盘点)
- [二、三层测试模型：main vs evolve-v2](#二三层测试模型main-vs-evolve-v2)
- [三、测试信号 → 原语改进路由表](#三测试信号--原语改进路由表)
- [四、落地计划](#四落地计划)

---

## 一、已有测试盘点

### main 分支（当前）

| 文件 | 测试数 | 测试内容 | 类型 |
|------|--------|----------|------|
| `tests/test_deploy.py` | 17 | deploy.sh 编译管线 | 规范化脚本测试 |
| `tests/test_app.py` | 1 | `/health` 端点 | API 测试 |
| `tests/test_create_workspace.py` | 3 | 脚手架创建 | 脚本测试 |
| **合计** | **21** | | 全部为规范化脚本测试 |

**运行结果**（Windows 11, 2026-03-25）：4 passed / 6 failed / 13 errors。
根因：Windows 下 `python3` 指向 App Store 占位符 + deploy.sh 无法直接执行（需 bash）。
CI/Linux 环境应正常通过。

### feat/evolve-v2 分支（待合并）

| 文件 | 测试数 | 测试内容 | 类型 |
|------|--------|----------|------|
| `tests/test_deploy.py` | 增强 | deploy.sh 编译管线（多平台适配） | 规范化脚本测试 |
| `tests/test_check_structure.py` | 4 | flow.yaml ↔ SKILL.md ↔ commitment 一致性 | 规范化脚本测试 |
| `tests/test_hooks.py` | 4 | Hook 脚本生成 + JSONL 日志格式 | 规范化脚本测试 |
| `tests/test_diagnose.py` | 3 | 诊断脚本 + 日志读取 + fulfillment 计算 | Commitment 测试 |
| `tests/test_eval_script.py` | 3 | eval_cases.yaml 执行 + pass/fail 评分 | 题集测试 |
| `tests/test_violations.py` | 2 | /violations API CRUD | API 测试 |

### evolve-v2 的 Evolver 运行时测试（非 pytest）

除 pytest 外，evolve-v2 还有 **Evolver Skill 驱动的运行时测试**：

| Evolver Skill | 测试类型 | 输入 | 运行方式 |
|---------------|----------|------|----------|
| `evolve_eval` | API 题集测试 | `eval_cases.yaml` | `run_eval.py` → HTTP 请求 → pass/fail |
| `evolve_auto` | 对话题集测试 | `conversation_tests/*.yaml` | `run_auto.py` → SDK adapter → 验证 Skill 触发 |
| `evolve_check` | 结构一致性校验 | 四原语源文件 | `check_structure.py` → JSON 报告 |
| `evolve_diagnose` | 运行时诊断 | Hook 日志 + commitment.yaml | `diagnose.py` → evolver LLM 判定 |

---

## 二、三层测试模型：main vs evolve-v2

| 测试层 | 用途 | main 状态 | evolve-v2 状态 |
|--------|------|-----------|---------------|
| **第一层：规范化脚本测试** | 验证编译管线和文件结构 | ✅ 已有（17 项） | ✅ 增强（+ check_structure + hooks） |
| **第二层：题集测试** | 验证 Agent 行为（API + 对话） | ❌ 不存在 | ✅ 已有（eval_cases.yaml + conversation_tests/） |
| **第三层：Commitment 测试** | 运行时指标诊断 | ❌ 不存在 | ✅ 已有（diagnose.py + violations API） |

### 覆盖范围对比

```
main 分支覆盖:

  agent/ 源文件 ──── deploy.sh ──── .runtime/ 产物
  (四原语)           ↑ 已测试 ↑      ↑ 已测试 ↑

  .runtime/ ──── Agent 执行 Skill ──── 用户体验
                 ↑ 未覆盖 ↑            ↑ 未覆盖 ↑


evolve-v2 分支覆盖:

  agent/ 源文件 ──── deploy.sh ──── .runtime/ 产物
  (四原语)           ↑ 已测试 ↑      ↑ 已测试 ↑
       ↑                                  │
       │ evolve_check                     │
       │ (一致性校验)                      ▼
       │                             Agent 执行
       │                                  │
       │ evolve_improve          evolve_eval (API)
       │ (证据驱动改进) ←──────── evolve_auto (对话)
       │         ↑               evolve_diagnose (运行时)
       │         │                     │
       └─────────┴─────────────────────┘
                   闭环
```

---

## 三、测试信号 → 原语改进路由表

### 第一层失败路由

| 测试信号 | 工具 | 改什么 | 原语层级 |
|----------|------|--------|----------|
| SOUL.md merge 失败 | test_deploy | scope/SOUL.md 或 role/*.md 格式 | Scope / Role |
| Skill symlink 断裂 | test_deploy | flow.yaml 注册 vs flow/ 目录不匹配 | Flow |
| commitment 引用无效 role/action | test_check_structure | commitment.yaml 的 from/to 字段 | Commitment |
| Hook 脚本未生成 | test_hooks | deploy.sh 的 hook 生成逻辑 | 基础设施 |
| commitment/eval 文件内容不一致 | test_deploy | 重新 deploy（.runtime/ 不应手动改） | Commitment |
| 幂等性失败 | test_deploy | deploy.sh 清理逻辑 | 基础设施 |

### 第二层失败路由

| 测试信号 | 工具 | 改什么 | 原语层级 |
|----------|------|--------|----------|
| API 返回错误状态码 | evolve_eval | src/app.py endpoint 实现 | Biz 层 |
| API 响应体不匹配 | evolve_eval | endpoint 逻辑或 eval_cases.yaml 期望值 | Biz 层 / 题集 |
| Agent 没触发预期 Skill | evolve_auto | SKILL.md 的 ## Trigger 描述 | Skill 内容 |
| Agent 触发了错误 Skill | evolve_auto | Trigger 冲突或 Scope 边界 | Flow / Scope |
| Agent 未触发任何 Skill | evolve_auto | flow.yaml 未注册或 Skill 未分配给该 role | Flow |

> evolve-v2 的 `references/failure-mapping.md` 和 `references/failure-analysis.md` 提供了更详细的映射指南。

### 第三层失败路由

| 测试信号 | 工具 | 改什么 | 原语层级 |
|----------|------|--------|----------|
| commitment VIOLATED（时间超限） | evolve_diagnose | 优化 Skill 执行步骤减少延迟 | Skill 内容 |
| commitment VIOLATED（顺序错误） | evolve_diagnose | flow.yaml 状态机 transitions | Flow |
| commitment INSUFFICIENT DATA | evolve_diagnose | Hook 采集覆盖不足或 App 使用量不够 | 基础设施 |
| fulfillment rate 持续低 | evolve_diagnose | 系统性问题 → 按第四章四层诊断 | 多层级 |
| /violations 堆积未解决 | test_violations | 缺少自动升级机制（on_violation） | Commitment |

> evolve-v2 的 `references/violation-mapping.md` 和 `references/judgment-examples.md` 提供了具体判定指南。

### 路由决策流程图

```
测试失败
  │
  ├─ 第一层（编译/结构）失败
  │     ├─ deploy.sh 报错          → 修 deploy.sh 或环境
  │     ├─ 文件结构不对             → 修四原语源文件
  │     └─ 一致性校验失败           → evolve_check 报告定位具体不匹配
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

### 已完成（evolve-v2 分支，待合并到 main）

```
✅ 第一层增强: test_check_structure.py + test_hooks.py
✅ 第二层实现: evolve_eval (API 题集) + evolve_auto (对话题集)
✅ 第三层实现: evolve_diagnose (运行时诊断) + test_violations.py
✅ Evolver 角色 + 5 个 Evolve Skill
✅ Hook 系统 (log_prompt.sh + log_tool.sh)
✅ commitment.yaml schema (from/to/condition/on_violation)
✅ 多平台 deploy (Claude/Codex/Kimi)
✅ 测试信号→原语路由 (references/ 下的 mapping 文档)
```

### 合并后待建

```
优先级 1: 修复 Windows 兼容性
  · test_deploy.py: run_deploy() 用 ["bash", deploy_sh]
  · deploy.sh: python3 → python fallback

优先级 2: Agent SDK Web 接入（iteration-guide 第八章）
  · BaseAdapter 升级为会话管理器 (create_session / send_message / close_session)
  · 通用 WebSocket handler (/ws/chat)
  · 这将使 evolve_auto 的对话测试也可通过 Web 层运行

优先级 3: deploy 变更摘要输出
  · deploy.sh 输出 [deploy] + Skill added / ~ Scope updated 等
  · 对 Dev 的迭代可观测性（iteration-guide 第六章）

优先级 4: 渐进自治的显式标注
  · evolver Skill 中标注当前自治等级（L1）
  · 随着验证通过率上升，逐步放开等级（iteration-guide 第九章 9.7）
```

### autoservice 参考架构的增强方向

> 来源：[autoservice-evolve-design.md](../../../autoservice/docs/socialware_0324/autoservice-evolve-design.md)

以下是 autoservice 设计中已详细规划、evolve-v2 尚未实现的增强点：

```
优先级 5: 四层诊断增强
  · evolve_diagnose 从单层诊断升级为 L1→L4 分层
  · L1: 数据层脚本（kb_checker 等价物）
  · L2: Prompt 质量题集
  · L3: 流程逻辑路径分析（trace_analyzer 等价物）
  · L4: 模型行为多次重复验证
  · 参考: autoservice-evolve-design.md §3

优先级 6: evaluator / evolver 角色分离
  · evaluator 只做测量（diagnose + batch-eval 两种模式）
  · evolver 只做改进（map → branch → compare → materialize）
  · 参考: autoservice-evolve-design.md §4

优先级 7: 蒙特卡洛分支验证
  · evolve_improve 从直接修改 → 生成 2-3 个 delta 变体
  · evaluator batch-eval 对各分支打分
  · skill_diff 对比 → 选最优 → materialize
  · 参考: autoservice-evolve-design.md §4

优先级 8: Commitment 自动升级
  · 同类问题 3 次出现 → 自动触发增加基线测试用例
  · 升级后验证闭环：全量回归 + 通过率不降 >5%
  · 参考: autoservice-evolve-design.md §5
```
