# 西窗 (XiChuang) - 多模态智能助手
# 多阶段构建 Dockerfile

# 第一阶段：构建前端
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web

# 复制前端依赖文件
COPY web/package.json web/package-lock.json ./

# 安装依赖
RUN npm ci

# 复制前端源代码
COPY web/ ./

# 构建前端
RUN npm run build

# 第二阶段：构建后端
FROM python:3.11-slim AS backend

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 安装系统依赖（包括 ffmpeg 用于音频处理）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    g++ \
    python3-dev \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制后端依赖文件
COPY server/pyproject.toml server/uv.lock ./

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r <(awk -F' = ' '/^dependencies = \[/ {p=1} p && /^\]$/ {p=0} p && /^[[:space:]]*"/ {gsub(/"/, "", $2); print $2}' pyproject.toml)

# 复制后端源代码
COPY server/src/ ./src/
COPY server/.env.example .env.example

# 复制前端构建产物到静态目录
COPY --from=frontend-builder /app/web/dist ./web/dist

# 创建必要的目录
RUN mkdir -p logs statics/images statics/audio statics/videos statics/files

# 暴露端口
EXPOSE 8000

# 健康检查（使用根路径，应用可能没有 /health 端点）
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 启动命令（需要用户提供 .env 文件或环境变量）
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]