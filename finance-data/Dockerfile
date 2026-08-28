# 金融数据中台 finance-data 镜像
# 基于官方 uv 镜像（内置 uv + Python 3.12）
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

# 1) 先复制依赖清单，利用 Docker 层缓存（源码变更不触发依赖重装）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) 复制源码、SQL schema、种子 CSV 与初始化脚本
COPY app ./app
COPY generate ./generate
COPY sql ./sql
COPY seeds ./seeds
COPY init_db.py ./
COPY docker/init-db.sh ./docker/init-db.sh

# 将 venv 内的 python / uvicorn 暴露到 PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# 默认启动 API（数据初始化由 db-init 一次性容器负责）
CMD ["python", "-m", "app.main"]
