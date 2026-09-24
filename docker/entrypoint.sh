#!/bin/sh
# 容器启动脚本：
# 1. 启动时安装 Python 依赖
# 2. 初始化 SQLite 数据库（幂等建表）
# 3. 启动 FastAPI 服务
set -e

echo "[entrypoint] 安装依赖 ..."
pip install --no-cache-dir -r requirements.txt

echo "[entrypoint] 初始化数据库 ..."
python -c "from app.database import init_db; init_db(); print('[entrypoint] 数据库就绪:', __import__('os').environ.get('DATABASE_PATH', '/data/kiln.db'))"

echo "[entrypoint] 启动 API (0.0.0.0:8000) ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
