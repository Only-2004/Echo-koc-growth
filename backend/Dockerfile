# Beacon 后端容器
# 用于 docker-compose 本地启动 / 腾讯云轻量服务器 / CloudBase 容器部署
#
# BUILD_ENV 控制是否安装 dev 依赖：
#   - dev（默认）：装 .[dev]，含 pytest / ruff / mypy（本地 docker-compose.yml 用）
#   - prod：只装 runtime 依赖，镜像小约 100MB（deploy/docker-compose.prod.yml 用）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先复制 pyproject.toml 利用 docker layer cache
COPY pyproject.toml /app/backend/pyproject.toml

ARG BUILD_ENV=dev
RUN pip install --upgrade pip \
    && cd /app/backend \
    && if [ "$BUILD_ENV" = "prod" ]; then \
         echo "==> Installing runtime deps only (prod)"; \
         pip install -e "."; \
       else \
         echo "==> Installing runtime + dev deps (dev)"; \
         pip install -e ".[dev]"; \
       fi

# 复制完整源码
COPY . /app/backend

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health').read()" || exit 1

EXPOSE 8000
WORKDIR /app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
