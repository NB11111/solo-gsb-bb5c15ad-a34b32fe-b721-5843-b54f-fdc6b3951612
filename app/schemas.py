"""请求/响应 Pydantic 模型。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PieceIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(..., ge=1, description="器物唯一编号（正整数）")
    volume: int = Field(..., ge=1, description="器物体积（正整数）")
    min_temp: int = Field(..., ge=1, description="允许烧成温度区间下界（含）")
    max_temp: int = Field(..., ge=1, description="允许烧成温度区间上界（含）")


class PlanCreate(BaseModel):
    kiln_capacity: int = Field(..., ge=1, description="单窑容量（正整数）")
    pieces: list[PieceIn] = Field(
        ..., min_length=1, max_length=14, description="1～14 件器物"
    )


class KilnLoadOut(BaseModel):
    pieces: list[int] = Field(..., description="本窑器物编号（升序）")
    total_volume: int = Field(..., description="本窑器物总体积")
    firing_temp: int = Field(..., description="本窑烧成温度（温度交集下界）")


class PlanOut(BaseModel):
    id: str
    kiln_count: int
    kiln_capacity: int
    kilns: list[KilnLoadOut]
    created_at: str
