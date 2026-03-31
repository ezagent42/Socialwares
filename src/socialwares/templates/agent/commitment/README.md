# Commitment

约束定义。描述角色之间的协作标准。

Commitment 在 `socialware.py` 中声明式定义：

```python
app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
    on_violation=("reviewer", "remind_review"),
)
```

`socialwares deploy` 编译后生成 `.runtime/commitment.yaml`。

详见 [Commitment 与 Evolve](../../docs/guides/004-commitment-and-evolve.md)。
