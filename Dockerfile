FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_PATH=/data/kiln.db

WORKDIR /app

# 先复制依赖清单，利用构建层缓存
COPY requirements.txt ./

COPY app ./app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /data

EXPOSE 8000

# 容器启动时安装依赖并初始化数据库，随后启动 API
ENTRYPOINT ["/entrypoint.sh"]
