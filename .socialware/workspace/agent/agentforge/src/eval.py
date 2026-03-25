"""Evaluation runner — executes commitments defined in eval.yaml."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class EvalResult:
    commitment_id: str
    description: str
    metric: str
    threshold: str
    value: float | None
    passed: bool


class EvalRunner:
    def __init__(self, eval_yaml: str | Path, db_path: str | Path | None = None):
        self.eval_yaml = Path(eval_yaml)
        self.db_path = Path(db_path) if db_path else None
        data = yaml.safe_load(self.eval_yaml.read_text(encoding="utf-8")) or {}
        self.commitments: dict = data.get("commitments", {})

    def run(self, commitment_id: str) -> EvalResult:
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
            commitment_id=commitment_id, description=c.get("description", ""),
            metric=c.get("metric", ""), threshold=c.get("threshold", ""),
            value=value, passed=passed,
        )

    def run_all(self) -> list[EvalResult]:
        return [self.run(cid) for cid in self.commitments]

    def _eval_sql(self, query: str) -> float | None:
        if not self.db_path or not self.db_path.exists():
            return None
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(query).fetchone()
            return float(row[0]) if row and row[0] is not None else None
        finally:
            conn.close()

    def _eval_api(self, endpoint: str) -> float | None:
        return None  # placeholder

    @staticmethod
    def _check_threshold(value: float | None, threshold: str) -> bool:
        if value is None or not threshold:
            return False
        match = re.match(r"([><=!]+)\s*([\d.]+)", threshold)
        if not match:
            return False
        op, target = match.group(1), float(match.group(2))
        ops = {">=": value >= target, "<=": value <= target, ">": value > target,
               "<": value < target, "==": value == target, "!=": value != target}
        return ops.get(op, False)
