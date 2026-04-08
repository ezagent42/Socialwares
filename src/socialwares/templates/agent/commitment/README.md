# Commitment

Collaboration constraints between roles.

Commitments are declared in `socialware.py`:

```python
app.commitment("C1",
    from_=("default", "submit_task"),
    to=("reviewer", "review_task"),
    condition="within 24h",
    on_violation=("reviewer", "remind_review"),
)
```

`socialwares deploy` compiles them into `.runtime/commitment.yaml`.
