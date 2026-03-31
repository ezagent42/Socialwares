# Flow — How

定义 Agent 能执行的操作（Skill）。

## 说明

此目录是仓库根的参考目录。实际 skill 文件在 `src/socialwares/templates/agent/flow/` 中。

`socialwares new` 创建项目时会从模板复制完整的 flow 目录到用户项目。

## 操作注册

操作在 `socialware.py` 中注册（而不是 flow.yaml）：

```python
app.action("check_health", role=["default"])
app.action("create_task", role=["default"])
app.action("evolve_structure_check", role=["evolver"])
```

每个操作对应 `agent/flow/{操作名}/SKILL.md`。

## 流转顺序（可选）

如果操作之间有固定的流转顺序：

```python
flow = app.flow("task_lifecycle", resource="task")
flow.states("draft", "submitted", "reviewed")
flow.transition("draft", "submit_task", "submitted", role=["default"])
```

`socialwares deploy` 编译后生成 `.runtime/flow.yaml`。
