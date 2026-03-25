# P3 完善 Commitment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add evaluation metrics system — define commitments in eval.yaml with executable eval methods, add /metrics API endpoint, and create evaluate + eval_report Skills for AgentForge.

**Architecture:** eval.yaml gains `eval_method` and `eval_query`/`eval_endpoint` fields. A lightweight EvalRunner in `src/eval.py` reads these and executes evaluations (SQL against Sqlite or HTTP against API). Results stored in `.runtime/data/Sqlite/`. Two new Skills teach AgentForge how to trigger evaluations and generate reports. Backend adds `/metrics` and `/eval` endpoints.

**Tech Stack:** Python (FastAPI, sqlite3, yaml), pytest

**Reference:** `docs/plans/2026-03-19-socialware-framework-design.md` (第四部分: Phase 3)

---

### Task 1: Create EvalRunner — evaluation execution engine

**Files:**
- Create: `src/eval.py`
- Test: `tests/test_eval.py`

**Step 1: Write the failing test**

Create `tests/test_eval.py`:

```python
"""Tests for evaluation runner."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml

from src.eval import EvalRunner, EvalResult


@pytest.fixture
def eval_config(tmp_path):
    """Create a minimal eval.yaml with test commitments."""
    eval_yaml = tmp_path / "eval.yaml"
    eval_yaml.write_text(yaml.dump({
        "commitments": {
            "C1": {
                "description": "Test metric >= 4.0",
                "metric": "test_score",
                "threshold": ">=4.0",
                "eval_method": "sql",
                "eval_query": "SELECT AVG(score) FROM scores",
            },
        }
    }))
    return eval_yaml


@pytest.fixture
def eval_db(tmp_path):
    """Create a test Sqlite database with sample data."""
    db_path = tmp_path / "socialware.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE scores (score REAL)")
    conn.executemany("INSERT INTO scores VALUES (?)", [(4.5,), (4.2,), (3.8,)])
    conn.commit()
    conn.close()
    return db_path


class TestEvalRunner:
    def test_load_commitments(self, eval_config):
        runner = EvalRunner(eval_config)
        assert "C1" in runner.commitments

    def test_run_sql_eval(self, eval_config, eval_db):
        runner = EvalRunner(eval_config, db_path=eval_db)
        result = runner.run("C1")
        assert isinstance(result, EvalResult)
        assert result.commitment_id == "C1"
        assert result.value is not None

    def test_eval_result_pass(self, eval_config, eval_db):
        runner = EvalRunner(eval_config, db_path=eval_db)
        result = runner.run("C1")
        # AVG(4.5, 4.2, 3.8) = 4.166... >= 4.0 → pass
        assert result.passed is True

    def test_eval_unknown_commitment(self, eval_config, eval_db):
        runner = EvalRunner(eval_config, db_path=eval_db)
        with pytest.raises(KeyError):
            runner.run("UNKNOWN")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_eval.py -v`
Expected: FAIL — `src.eval` module doesn't exist.

**Step 3: Implement EvalRunner**

Create `src/eval.py`:

```python
"""Evaluation runner — executes commitments defined in eval.yaml.

Reads eval.yaml, runs evaluations (SQL or API), returns results.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class EvalResult:
    """Result of evaluating a single commitment."""
    commitment_id: str
    description: str
    metric: str
    threshold: str
    value: float | None
    passed: bool


class EvalRunner:
    """Runs evaluations defined in eval.yaml."""

    def __init__(self, eval_yaml: str | Path, db_path: str | Path | None = None):
        self.eval_yaml = Path(eval_yaml)
        self.db_path = Path(db_path) if db_path else None

        data = yaml.safe_load(self.eval_yaml.read_text(encoding="utf-8")) or {}
        self.commitments: dict = data.get("commitments", {})

    def run(self, commitment_id: str) -> EvalResult:
        """Run a single commitment evaluation."""
        if commitment_id not in self.commitments:
            raise KeyError(f"Commitment '{commitment_id}' not found")

        c = self.commitments[commitment_id]
        method = c.get("eval_method", "manual")

        value = None
        if method == "sql" and self.db_path:
            value = self._eval_sql(c["eval_query"])
        elif method == "api":
            value = self._eval_api(c.get("eval_endpoint", ""))

        passed = self._check_threshold(value, c.get("threshold", ""))

        return EvalResult(
            commitment_id=commitment_id,
            description=c.get("description", ""),
            metric=c.get("metric", ""),
            threshold=c.get("threshold", ""),
            value=value,
            passed=passed,
        )

    def run_all(self) -> list[EvalResult]:
        """Run all commitment evaluations."""
        return [self.run(cid) for cid in self.commitments]

    def _eval_sql(self, query: str) -> float | None:
        """Execute SQL query against Sqlite database."""
        if not self.db_path or not self.db_path.exists():
            return None
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(query).fetchone()
            return float(row[0]) if row and row[0] is not None else None
        finally:
            conn.close()

    def _eval_api(self, endpoint: str) -> float | None:
        """Call an API endpoint and extract a numeric value."""
        # P3 placeholder — will be implemented when API metrics exist
        return None

    @staticmethod
    def _check_threshold(value: float | None, threshold: str) -> bool:
        """Check if value meets threshold (e.g. '>=4.0', '<=72')."""
        if value is None or not threshold:
            return False
        match = re.match(r"([><=!]+)\s*([\d.]+)", threshold)
        if not match:
            return False
        op, target = match.group(1), float(match.group(2))
        ops = {">=": value >= target, "<=": value <= target, ">": value > target,
               "<": value < target, "==": value == target, "!=": value != target}
        return ops.get(op, False)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_eval.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/eval.py tests/test_eval.py
git commit -m "feat(eval): add EvalRunner for executing commitment evaluations"
```

---

### Task 2: Add /metrics and /eval API endpoints

**Files:**
- Modify: `src/app.py`
- Modify: `tests/test_chat_api.py`

**Step 1: Write the failing test**

Add to `tests/test_chat_api.py`:

```python
class TestMetrics:
    def test_get_metrics(self):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_post_eval(self):
        r = client.post("/eval", json={"commitment_id": "all"})
        # May return empty results if no commitments defined
        assert r.status_code in (200, 404)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_chat_api.py::TestMetrics -v`
Expected: FAIL — endpoints don't exist.

**Step 3: Add endpoints to src/app.py**

Add to `src/app.py`:

```python
from src.eval import EvalRunner, EvalResult

@app.get("/metrics")
async def get_metrics():
    """Return latest evaluation results for all commitments."""
    eval_yaml = AGENT_DIR / "commitment" / "eval.yaml"
    if not eval_yaml.exists():
        return {"metrics": []}
    db_path = RUNTIME_DIR / "data" / "Sqlite" / "socialware.db"
    runner = EvalRunner(eval_yaml, db_path=db_path if db_path.exists() else None)
    results = runner.run_all()
    return {"metrics": [
        {"id": r.commitment_id, "description": r.description,
         "metric": r.metric, "threshold": r.threshold,
         "value": r.value, "passed": r.passed}
        for r in results
    ]}

@app.post("/eval")
async def run_eval(req: dict):
    """Run evaluation for a specific commitment or all."""
    eval_yaml = AGENT_DIR / "commitment" / "eval.yaml"
    if not eval_yaml.exists():
        raise HTTPException(404, "eval.yaml not found")
    db_path = RUNTIME_DIR / "data" / "Sqlite" / "socialware.db"
    runner = EvalRunner(eval_yaml, db_path=db_path if db_path.exists() else None)
    cid = req.get("commitment_id", "all")
    if cid == "all":
        results = runner.run_all()
    else:
        results = [runner.run(cid)]
    return {"results": [
        {"id": r.commitment_id, "passed": r.passed, "value": r.value, "threshold": r.threshold}
        for r in results
    ]}
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_chat_api.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/app.py tests/test_chat_api.py
git commit -m "feat(api): add /metrics and /eval endpoints for commitment evaluation"
```

---

### Task 3: Create evaluate and eval_report Skills for AgentForge

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/evaluate/SKILL.md`
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/eval_report/SKILL.md`
- Modify: `.socialware/workspace/my-team/agentforge/agent/flow/flow.yaml`
- Modify: `tests/test_agentforge.py`

**Step 1: Write the failing test**

Add to `tests/test_agentforge.py` in `TestAgentforgeSkills`:

```python
    def test_evaluate_skill_exists(self):
        skill = AGENTFORGE_DIR / "agent" / "flow" / "evaluate" / "SKILL.md"
        assert skill.exists()

    def test_eval_report_skill_exists(self):
        skill = AGENTFORGE_DIR / "agent" / "flow" / "eval_report" / "SKILL.md"
        assert skill.exists()
```

Update `EXPECTED_SKILLS` list to include `"evaluate"` and `"eval_report"`.

**Step 2: Run test to verify it fails**

**Step 3: Create SKILL.md files and update flow.yaml**

Create `evaluate/SKILL.md`:
```markdown
---
name: evaluate
description: "Run commitment evaluations and check if Agent meets defined standards"
---

# Evaluate Commitments

## Trigger

User says "evaluate", "check metrics", "run eval", "how is the agent doing", etc.

## Flow

1. Read `agent/commitment/eval.yaml` to list defined commitments
2. Call `POST /eval` with `{"commitment_id": "all"}` to run all evaluations
3. Display results: commitment description, current value, threshold, pass/fail
4. If any commitment fails, suggest improvements

## API

```bash
# Run all evaluations
curl -X POST http://localhost:8001/eval -H "Content-Type: application/json" -d '{"commitment_id": "all"}'

# Get latest metrics
curl http://localhost:8001/metrics
```
```

Create `eval_report/SKILL.md`:
```markdown
---
name: eval_report
description: "Generate a summary report of all commitment evaluation results"
---

# Evaluation Report

## Trigger

User says "eval report", "show report", "commitment status", "quality report", etc.

## Flow

1. Call `GET /metrics` to get all evaluation results
2. Format as a readable report with:
   - Overall pass rate
   - Per-commitment status (pass/fail, value vs threshold)
   - Trend if historical data available
3. Suggest actions for failing commitments

## API

```bash
curl http://localhost:8001/metrics
```
```

Update flow.yaml to add entries for both.

**Step 4: Run test to verify it passes**

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/evaluate/
git add .socialware/workspace/my-team/agentforge/agent/flow/eval_report/
git add .socialware/workspace/my-team/agentforge/agent/flow/flow.yaml
git add tests/test_agentforge.py
git commit -m "feat(agentforge): add evaluate and eval_report skills for P3 commitment"
```

---

### Task 4: Full verification

**Step 1:** Run all tests: `python -m pytest tests/ -v`
**Step 2:** Verify /metrics and /eval endpoints via curl
**Step 3:** Final commit

---

## Summary

| Task | What | Key Files |
|------|------|-----------|
| 1 | EvalRunner engine | `src/eval.py`, `tests/test_eval.py` |
| 2 | /metrics + /eval endpoints | `src/app.py`, `tests/test_chat_api.py` |
| 3 | evaluate + eval_report Skills | AgentForge flow/ + flow.yaml |
| 4 | Full verification | All tests pass |
