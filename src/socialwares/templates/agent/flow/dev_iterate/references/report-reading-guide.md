# Evolve 报告解读参考

## 报告类型

| 文件名前缀 | 来源 Skill | 内容 |
|-----------|-----------|------|
| `check_*.json` | evolve_structure_check | 四原语一致性检查 |
| `eval_*.json` | evolve_api_check | API 端点测试结果 |
| `diagnose_*.json` | evolve_session_diagnose | 对话数据诊断 |

## 报告格式

```json
{
  "type": "check | eval | diagnose",
  "timestamp": "ISO 8601",
  "score": 0.0-1.0,
  "passed": 4,
  "total": 4,
  "summary": "human-readable summary",
  "details": ["issue 1", "issue 2"],
  "suggestions": [
    {
      "primitive": "flow | role | scope | commitment",
      "action": "what to do",
      "reason": "why"
    }
  ]
}
```

## 改进优先级

1. **结构问题**（structure check failures）— 阻塞其他检查
2. **API 失败**（eval failures）— 功能不可用
3. **覆盖率不足**（eval suggestions）— 测试缺失
4. **Commitment 违反**（diagnose violations）— 协作质量
5. **Scope 差距**（scope gaps）— 声明与实现不一致

## 常见修复模式

### 缺少 SKILL.md
```bash
mkdir -p agent/flow/{action}
# 写 SKILL.md
# 在 socialware.py 注册 app.action("action", role=[...])
socialwares deploy
```

### 缺少 eval case
```yaml
# agent/flow/evolve_api_check/eval_cases.yaml 添加：
- description: "Test {action}"
  method: POST
  endpoint: /api/{resource}
  body: '{"key": "value"}'
  expected_status: 200
```

### Commitment 违反
检查 SKILL.md 中的 Flow 步骤是否引导角色完成承诺的动作。
