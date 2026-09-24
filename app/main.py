"""共窑排程 API：FastAPI 应用入口。"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import database
from .scheduler import Piece, SchedulingError, solve
from .schemas import PlanCreate, PlanOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 容器启动：初始化数据库（幂等建表）
    database.init_db()
    yield


app = FastAPI(
    title="陶艺工作室共窑排程 API",
    description="按器物温度区间与体积，用位掩码动态规划求最少窑次的装窑方案。",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(SchedulingError)
async def scheduling_error_handler(_request, exc: SchedulingError):
    """业务不可排程（如单件超容量、编号重复）：400 + 明确错误信息。"""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


@app.post("/plans", response_model=PlanOut, status_code=201, tags=["plans"])
async def create_plan(payload: PlanCreate):
    pieces = [
        Piece(
            piece_id=p.id,
            volume=p.volume,
            min_temp=p.min_temp,
            max_temp=p.max_temp,
        )
        for p in payload.pieces
    ]
    loads = solve(pieces, payload.kiln_capacity)

    plan = {
        "id": str(uuid.uuid4()),
        "kiln_count": len(loads),
        "kiln_capacity": payload.kiln_capacity,
        "kilns": [
            {
                "pieces": list(load.pieces),
                "total_volume": load.total_volume,
                "firing_temp": load.firing_temp,
            }
            for load in loads
        ],
        "created_at": database.utc_now_iso(),
    }
    database.save_plan(plan)
    return plan


@app.get("/plans/{plan_id}", response_model=PlanOut, tags=["plans"])
async def get_plan(plan_id: str):
    plan = database.get_plan(plan_id)
    if plan is None:
        return JSONResponse(
            status_code=404, content={"detail": f"方案不存在: {plan_id}"}
        )
    return plan
