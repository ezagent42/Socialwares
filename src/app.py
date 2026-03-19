"""Socialware App 后端 — FastAPI 入口。

最小模板，随渐进生长扩展。
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Socialware App",
    description="Agent 交互可视化的 Web 应用",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """健康检查。"""
    return {"status": "ok"}
