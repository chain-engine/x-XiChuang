# -*- coding: utf-8 -*-
"""
FastAPI 应用入口

创建并配置 FastAPI 应用实例，注册路由和中间件。
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.core.exceptions import register_exception_handlers
from src.core.logger import logger, setup_logging
from src.core.middleware import (
    ApiKeyMiddleware,
    ExceptionHandlingMiddleware,
    RequestIDMiddleware,
    RequestLoggingMiddleware,
)
from src.api.router import api_router


# ============ IOC 容器配置 ============

def _configure_container() -> None:
    """配置依赖注入容器，注册服务接口到实现的映射。"""
    from src.core.container import Container, Lifecycle
    from src.services.base import IChatService, IMilvusService
    from src.services.chat_service import ChatService
    from src.services.milvus_service import MilvusService

    container = Container.get_instance()
    container.register(IChatService, ChatService, Lifecycle.SINGLETON)
    container.register(IMilvusService, MilvusService, Lifecycle.SINGLETON)
    logger.info("IOC container configured")


# ============ 应用生命周期管理 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    包含启动和关闭时的资源初始化和清理逻辑。
    """
    # 启动时
    setup_logging()
    logger.info("Starting application: %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Environment: %s, Debug: %s", settings.ENVIRONMENT, settings.DEBUG)

    # 配置 IOC 容器
    _configure_container()

    # 初始化数据库
    try:
        from src.infras.database import async_init_db
        await async_init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning("Database initialization skipped: %s", e)

    # 确保日志目录存在
    settings.LOG_DIR_PATH.mkdir(parents=True, exist_ok=True)

    yield

    # 关闭时
    logger.info("Shutting down application...")

    # 关闭数据库连接
    try:
        from src.infras.database import async_engine
        await async_engine().dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning("Error closing database: %s", e)


# ============ 应用工厂 ============

def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例

    Returns:
        配置完成的 FastAPI 应用实例
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="多模态智能助手 - 支持文本、语音、图片、视频对话",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ============ 注册异常处理器 ============
    register_exception_handlers(app)

    # ============ 注册中间件 ============
    # CORS 中间件
    cors_origins = settings.CORS_ORIGINS
    if settings.CORS_ALLOW_CREDENTIALS and "*" in cors_origins:
        cors_origins = ["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:5173", "http://127.0.0.1:8000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)

    # 异常处理中间件
    app.add_middleware(ExceptionHandlingMiddleware)

    # API Key 鉴权中间件
    app.add_middleware(ApiKeyMiddleware)

    # 请求 ID 中间件
    app.add_middleware(RequestIDMiddleware)

    # ============ 注册路由 ============

    # API 路由（统一前缀 /api）
    app.include_router(api_router, prefix="/api")

    # ============ 静态文件挂载 ============

    _mount_static_files(app)

    # ============ 前端页面路由 ============

    _setup_frontend_routes(app)

    # ============ 启动日志 ============

    logger.info("Application created successfully")
    logger.info("API Documentation: /docs")
    logger.info("API ReDoc: /redoc")

    return app


def _project_root() -> Path:
    """
    项目根目录路径解析。

    优先级：
    1. 环境变量 XICHUANG_PROJECT_ROOT（Docker / 自定义部署使用）
    2. src/main.py 的 parents[1]（本地开发 / uv pip install -e 场景）
    """
    env_root = os.getenv("XICHUANG_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    # src/main.py → parents[0]=src, parents[1]=项目根
    return Path(__file__).resolve().parents[1]


def _mount_static_files(app: FastAPI) -> None:
    """挂载静态文件目录"""
    project_root = _project_root()
    statics_dir = project_root / settings.STATIC_DIR

    if statics_dir.exists():
        app.mount("/statics", StaticFiles(directory=str(statics_dir)), name="statics")
        logger.info("Static files mounted: %s", statics_dir)

    # 前端构建产物
    dist_dir = project_root / "web" / "dist"
    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
            logger.info("Frontend assets mounted: %s", assets_dir)
    else:
        logger.warning("Frontend dist not found at %s; root path will return 503", dist_dir)


def _setup_frontend_routes(app: FastAPI) -> None:
    """配置前端路由"""

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index() -> HTMLResponse:
        """返回前端首页"""
        project_root = _project_root()
        dist_dir = project_root / "web" / "dist"
        index_path = dist_dir / "index.html"

        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                return HTMLResponse(f.read())

        dev_index = project_root / "web" / "index.html"
        if dev_index.exists():
            with open(dev_index, "r", encoding="utf-8") as f:
                return HTMLResponse(f.read())

        return HTMLResponse(
            "<h1>Frontend not built. Run: cd web && npm run build</h1>",
            status_code=503,
        )

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        include_in_schema=False,
    )
    async def catch_all(request: Request, full_path: str):
        """SPA 路由兜底 + API 404 处理"""
        project_root = _project_root()
        dist_dir = project_root / "web" / "dist"

        # API 路径返回 404
        if full_path.startswith("api/"):
            return JSONResponse(
                {"detail": f"API endpoint /{full_path} not found"},
                status_code=404,
            )

        # 尝试返回静态文件
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # 返回 index.html（SPA 路由兜底）
        index_path = dist_dir / "index.html"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                return HTMLResponse(f.read())

        return HTMLResponse("<h1>Page not found</h1>", status_code=404)


# ============ 创建应用实例 ============

app = create_app()


# ============ 直接运行入口 ============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
