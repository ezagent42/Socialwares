# Commitment — What

定义 Eval 指标、SLA 和承诺。

## 文件

- `eval.yaml` — Commitment 定义

## eval.yaml 格式

```yaml
commitments:
  C1:
    description: "描述承诺内容"
    trigger_state: submitted       # 哪个状态触发计时
    deadline_hours: 72             # 超时时间
    debtor_role: reviewer          # 谁负责履行
    creditor_role: submitter       # 谁是受益方
    escalation_role: admin         # 超时后升级给谁
```

## deploy.sh 处理

`eval.yaml` 会被复制到每个 role 的 `.runtime/agents/{name}/eval.yaml`。
