"""Socialware App 后端 — FastAPI 入口。

最简模板。用户在此基础上渐进生长 (P1→P5)。
启动: uvicorn src.app:app --port 8001
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Socialware App",
    description="Agent 交互可视化的 Web 应用",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
