# 西窗 (XiChuang) - 多模态智能助手
# 多阶段构建 Dockerfile

# ============ 第一阶段：构建前端 ============
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web

# 复制前端依赖文件并安装
COPY web/package.json web/package-lock.json ./
RUN npm ci

# 复制前端源代码并构建
COPY web/ ./
RUN npm run build

# ============ 第二阶段：构建后端 ============
FROM python:3.11-slim AS backend

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai \
    # uvicorn 默认工作目录就是 /app，src 模块在 /app/src/main.py
    PYTHONPATH=/app

WORKDIR /app

# 安装系统依赖：ffmpeg（音频处理）、gcc（编译客户端）、curl（健康检查）
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        gcc \
        g++ \
        python3-dev \
        default-libmysqlclient-dev \
        pkg-config \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip + 安装 uv（用于真正用 lock 文件安装依赖）
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir uv

# 复制后端依赖文件（先单独拷贝以利用 Docker 缓存）
COPY server/pyproject.toml server/uv.lock ./

# 使用 uv sync 严格按 lock 文件安装；不要安装 dev 组（pytest/ruff/mypy 等）
RUN uv sync --frozen --no-dev --no-install-project

# 复制后端源代码
COPY server/src/ ./src/

# 复制 .env 模板（实际部署应通过环境变量或挂载注入 .env）
COPY server/.env.example .env.example

# 复制前端构建产物到 /app/web/dist
COPY --from=frontend-builder /app/web/dist ./web/dist

# 创建运行时目录（日志、上传文件）
RUN mkdir -p logs statics/images statics/audio statics/videos statics/files \
    && chmod -R 755 logs statics

# 暴露端口
EXPOSE 8000

# 健康检查：使用专用 live 端点，不要用 / （那是 SPA 兜底 HTML）
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health/live || exit 1

# 启动命令：模块路径是 src.main:app（见 server/src/main.py）
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]