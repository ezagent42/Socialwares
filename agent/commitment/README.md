# Commitment — What

定义可追踪的承诺和评估标准。

## 核心概念

Commitment 是**声明式**的：描述"什么算达标"，不规定"怎么检查"。

执行方式由 App 的 Biz 层 (`src/`) 决定，例如：
- API middleware 自动检查
- Cron 定时评估
- Eval 脚本按需运行
- Agent 自主检查

## 文件

- `eval.yaml` — Commitment 声明

## eval.yaml 格式

```yaml
commitments:
  C1:
    description: "描述承诺内容"
    metric: metric_name          # 评估指标名
    threshold: ">=4.5"           # 达标阈值 (格式自由)
    debtor_role: reviewer        # 谁负责 (可选)
    creditor_role: submitter     # 谁受益 (可选)
```

Commitment 不限于时间 SLA，可以是任何可衡量的标准：
- 时间: "72h 内完成审核"
- 质量: "客户满意度 ≥ 4.5"
- 数量: "每周完成 ≥ 3 个任务"
- 自定义: 任何 App 特定的评估指标

## deploy.sh 处理

`eval.yaml` 会被复制到每个 role 的 `.runtime/agents/{name}/eval.yaml`，
供 Agent 在运行时参考承诺标准。
