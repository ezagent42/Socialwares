"""Tests for EvalRunner."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml

from src.eval import EvalRunner, EvalResult


@pytest.fixture
def eval_config(tmp_path):
    f = tmp_path / "eval.yaml"
    f.write_text(yaml.dump({
        "commitments": {
            "C1": {
                "description": "Score >= 4.0",
                "metric": "score",
                "threshold": ">=4.0",
                "eval_method": "sql",
                "eval_query": "SELECT AVG(score) FROM scores",
            }
        }
    }))
    return f


@pytest.fixture
def eval_db(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE scores (score REAL)")
    conn.executemany("INSERT INTO scores VALUES (?)", [(4.5,), (4.2,), (3.8,)])
    conn.commit()
    conn.close()
    return db


class TestEvalRunner:
    def test_load(self, eval_config):
        assert "C1" in EvalRunner(eval_config).commitments

    def test_run_sql(self, eval_config, eval_db):
        r = EvalRunner(eval_config, db_path=eval_db).run("C1")
        assert isinstance(r, EvalResult)
        assert r.value is not None

    def test_pass(self, eval_config, eval_db):
        assert EvalRunner(eval_config, db_path=eval_db).run("C1").passed is True

    def test_unknown(self, eval_config, eval_db):
        with pytest.raises(KeyError):
            EvalRunner(eval_config, db_path=eval_db).run("X")

    def test_run_all(self, eval_config, eval_db):
        assert len(EvalRunner(eval_config, db_path=eval_db).run_all()) == 1

    def test_empty(self, tmp_path):
        f = tmp_path / "e.yaml"
        f.write_text("commitments: {}")
        assert EvalRunner(f).run_all() == []
