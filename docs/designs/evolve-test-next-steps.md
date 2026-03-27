# Evolve & Test 进化分析与下一步

> 基于 iteration-guide.md + testing-status.md + autoservice 参考文档的全文通读，分析当前 evolve/test 框架的实际状态，识别待明确的决策点，给出优先级推荐。
>
> 日期：2026-03-27

---

## 目录

- [一、现状诊断：框架空转](#一现状诊断框架空转)
- [二、Evolve 待明确的决策点](#二evolve-待明确的决策点)
- [三、Test 待明确的决策点](#三test-待明确的决策点)
- [四、优先级推荐](#四优先级推荐)
- [五、明确不推荐现在做的](#五明确不推荐现在做的)

---

## 一、现状诊断：框架空转

```
已建好的                              缺少的
────────                             ────────
✅ 5 个 Evolve Skill + 脚本           ❌ 没有一个真实 App 跑过 P1→P5
✅ Hook 采集机制                      ❌ 没有一条真实的 Hook 日志
✅ commitment.yaml schema             ❌ commitments: {} 是空的
✅ eval_cases.yaml 框架               ❌ 只有 1 条 health check
✅ conversation_tests/ 框架           ❌ 只有 1 条 check_health
✅ diagnose → improve 闭环代码        ❌ 从未真正运行过这个闭环
✅ 8 个 pytest 文件                   ❌ Windows 下跑不过
```

**核心问题**：工厂建好了，但还没有产品跑过产线。所有 iteration-guide 和 testing-status 中标注的"待补充"都指向同一个根因——**缺一个真实 App 实例走完 P1→P3**。

这意味着：当前所有框架增强（四层诊断、角色分离、蒙特卡洛）都是在**没有实证数据**的情况下设计的。在管线流动之前，任何框架优化都是猜测。

---

## 二、Evolve 待明确的决策点

### E1: evolver 的自治边界靠什么约束？

**现状**：evolver 的 `allowed_tools` 是 7 个（Bash+Read+Write+Edit+Glob+Grep+Skill），这意味着 evolver 已具备 L3（写代码）的能力。但 iteration-guide 第九章说 L1 只改 SKILL.md 内容。

**冲突**：工具白名单给了 L3 的能力，文档约束在 L1。实际靠什么保证 evolver 不越界？

**选项**：
- A：靠 evolver.md（SOUL.md）的自然语言约束（"只改 SKILL.md 内容"）
- B：靠工具白名单限制（L1 阶段只给 Read+Bash，不给 Write/Edit）
- C：靠文件路径白名单（允许 Write/Edit，但限制只能改 `agent/flow/*/SKILL.md`）

**推荐**：短期用 A（SOUL.md 约束），因为 evolver 还没跑过一次，过早收紧工具会阻碍调试。中期实现 C（路径白名单），作为 L 等级切换的技术手段。

### E2: evolve_improve 直接改 vs 走 PR？

**现状**：improve SKILL.md 写"propose and apply"，暗示直接修改文件。但 9.3 节说"模式 B 修改 agent/ 需要 PR + Dev review"。

**冲突**：improve 到底是直接改文件，还是生成 diff 等 Dev 审批？

**推荐**：
- `.runtime/` 内的修改（Path A）→ 直接改，save_report 记录即可
- `agent/` 内的修改（Path B）→ improve 创建新 branch + commit，Dev review 后合并
- 当前阶段（L0/L1）：所有 improve 都先做成"提案"（输出 diff + 理由），Dev 手动 apply

### E3: diagnose 的触发时机

**现状**：靠人工触发（evolver TUI 中输入 "diagnose"）。文档多处提到"Cron 定时触发"、"指标低于阈值自动触发"，但无任何自动触发实现。

**推荐**：P3 阶段实现，最简方案：
```bash
# Makefile 加一条
make evolve-cycle ROLE=evolver
# 内部: start_agent.py --role evolver --prompt "run check, then diagnose, then evaluate"
```
Cron 只需 `0 2 * * * cd /workspace && make evolve-cycle`，不需要复杂的事件驱动。

### E4: commitment condition 的表达力

**现状**：自然语言条件（"within 24h"），evolver LLM 做判断。

**待明确**：不同 LLM（Claude vs Codex vs Kimi）判断一致性如何保证？换 adapter 后同一 condition 还能判对吗？

**推荐**：短期可接受（LLM 判断 + 人工 review 报告）。中期为常见模式提供结构化字段：
```yaml
# 结构化 condition 示例（未来增强）
condition:
  type: time_limit
  from_event: submit_code
  to_event: review_code
  max_duration: "24h"
```
这样脚本可直接计算，不依赖 LLM 判断。自然语言 condition 保留为 fallback。

### E5: references/ 子目录的内容策略

**现状**：模板级别（空或极简）。

**推荐**：**先删除空模板**，等有真实案例后再补。空 reference 比无 reference 更有害——可能误导 evolver 生成低质量的判断。在首次完整 evolve 闭环跑通后，用实际的失败案例填充。

---

## 三、Test 待明确的决策点

### T1: pytest vs evolve Skill 测试的关系

**现状**：两套并行——pytest（CI 跑）+ evolve_*（evolver 跑）。例如 `test_eval_script.py` 测试 run_eval.py 脚本能跑，`evolve_api_check` 测试 API 实际行为。

**待明确**：两者重叠但不相同，关系需要理清。

**推荐**：

| 维度 | pytest | evolve_* Skill |
|------|--------|---------------|
| **验证什么** | 框架本身（脚本能跑、格式正确） | 业务行为（Agent 做对了吗） |
| **谁跑** | CI / Dev 本地 | evolver 角色 |
| **何时跑** | 每次 commit / PR | 按需或定时 |
| **失败含义** | 框架有 bug | 业务有问题 |

两者职责不同，不冲突。但文档应明确区分，避免混淆。

### T2: Windows 兼容性修复的优先级

**现状**：deploy.sh 相关测试在 Windows 下全挂。

**推荐**：取决于开发环境——
- Dev 主要在 Windows 上开发 → **优先级 1**，阻断日常开发体验
- 仅在 CI/Linux 上跑测试 → 可延后，但需要在 README 中说明

### T3: 题集的增长策略

**现状**：每加一个 Skill 加一条题集（"能触发"测试）。

**推荐**：每个 Skill 至少 3 条题集：

```yaml
# conversation_tests/default.yaml — 以 create_task 为例

# ① 正向触发
- input: "create a task called Review PR"
  expected_skill: create_task
  expected_contains: ["created", "task"]

# ② 边界（近似但不该触发的输入）
- input: "what tasks do I have"
  expected_skill: list_tasks        # 不应触发 create_task
  expected_not_contains: ["created"]

# ③ 质量（回复包含关键信息）
- input: "create a task for updating docs by Friday"
  expected_skill: create_task
  expected_contains: ["Friday", "docs"]  # 验证 Agent 保留了关键信息
```

---

## 四、优先级推荐

### 阶段一：让管线流动（1-2 周）

```
① 用真实 App 走完 P1→P2
   · 在 default workspace 定义真实业务场景（如 Task Manager）
   · scope/scope.md 填入真实 Capabilities
   · 加 3-5 个业务 Skill + 对应 API endpoint

② 同步扩充题集
   · eval_cases.yaml: 每个 API endpoint 一条
   · conversation_tests/: 每个 Skill 3 条（正向/边界/质量）

③ 跑一次完整的 evolve 五步
   · make start ROLE=evolver
   · check → diagnose → api_check → auto → improve
   · 记录：哪些环节顺畅，哪些卡住

④ 修复 Windows 兼容性（如果 Dev 在 Windows 上工作）
   · test_deploy.py: ["bash", deploy_sh]
   · deploy.sh: python3 → python fallback

产出：第一次真实的 evolve 报告 + 管线是否能跑的实证
```

### 阶段二：填充 Commitment，解锁 L1（1 周）

```
⑤ P3：填入 2-3 条 commitment
   · 时间类："create_task 后 list_tasks 应在 5s 内包含新任务"
   · 顺序类："submit 必须在 review 之前"

⑥ 产生 Hook 日志
   · 实际使用 App 一段时间，积累 prompts/current.jsonl 数据

⑦ 跑 diagnose → 第一次真实的 FULFILLED/VIOLATED 判定
   · 验证 commitment condition 的自然语言判断是否准确

⑧ 跑 improve → evolver 基于真实报告改进 SKILL.md
   · L1 自迭代闭环首次运行

产出：L1 解锁的实证 + commitment 判定准确性的数据
```

### 阶段三：基于实证优化框架（持续）

```
⑨ 根据阶段一二的经验，做数据驱动的决策：
   · references/ 该填什么 → 用阶段一二的真实失败案例
   · commitment condition 是否需要结构化 → 看 LLM 判断准确率
   · evolve_improve 是否需要 PR 机制 → 看 improve 的质量和风险
   · evaluator/evolver 是否需要分离 → 看单 evolver 的瓶颈在哪
   · L1→L4 四层诊断是否需要 → 看单层诊断够不够用

产出：基于实证的框架优化路线图
```

---

## 五、明确不推荐现在做的

| 不推荐 | 原因 |
|--------|------|
| evaluator/evolver 角色分离 | 单一 evolver 还没跑过一次完整闭环，分离是过早优化 |
| 蒙特卡洛分支验证 | 连一次 improve 都没跑过，多方案对比更是过早 |
| Prompt 覆盖冲突四方案 | 当前只有 default workspace，无多租户场景 |
| Agent SDK Web 接入 | 先通过 TUI/SDK 模式验证完整闭环，Web 层是锦上添花 |
| L1→L4 四层诊断增强 | 当前 diagnose 一层都没跑过真实数据，分四层无从验证 |
| Commitment 自动升级 | 连第一条 commitment 都没有，自动升级无从谈起 |
| Workspace 迁移方案 | 当前仅有 default workspace，无迁移需求 |

**原则**：先让 0→1 跑通，再谈 1→N 的优化。iteration-guide 和 autoservice 设计文档中规划的增强方向都是对的，但需要真实数据来验证优先级和必要性。

---

## 变更记录

| 日期 | 内容 |
|------|------|
| 2026-03-27 | 初始创建：现状诊断 + 5 个 Evolve 决策点 + 3 个 Test 决策点 + 三阶段推荐 |
