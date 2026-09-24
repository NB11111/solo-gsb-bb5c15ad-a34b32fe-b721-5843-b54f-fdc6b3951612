"""SQLite 存储层（标准库 sqlite3，容器启动时自动初始化）。"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.environ.get("DATABASE_PATH", "/data/kiln.db")

_write_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
    id            TEXT PRIMARY KEY,
    kiln_count    INTEGER NOT NULL,
    kiln_capacity INTEGER NOT NULL,
    kilns         TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """幂等建表，容器启动时调用。"""
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def save_plan(plan: dict[str, Any]) -> None:
    """保存一条排程方案。"""
    with _write_lock, _connect() as conn:
        conn.execute(
            "INSERT INTO plans (id, kiln_count, kiln_capacity, kilns, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                plan["id"],
                plan["kiln_count"],
                plan["kiln_capacity"],
                json.dumps(plan["kilns"], ensure_ascii=False),
                plan["created_at"],
            ),
        )


def get_plan(plan_id: str) -> dict[str, Any] | None:
    """按 ID 读取排程方案，不存在返回 None。"""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, kiln_count, kiln_capacity, kilns, created_at "
            "FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "kiln_count": row["kiln_count"],
        "kiln_capacity": row["kiln_capacity"],
        "kilns": json.loads(row["kilns"]),
        "created_at": row["created_at"],
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
