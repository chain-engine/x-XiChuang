# -*- coding: utf-8 -*-
"""
FastAPI 应用工厂

创建并配置 FastAPI 应用实例。
"""

import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from src.config.settings import settings
from src.core.logger import logger
from src.app.routers import chat, milvus, conversations


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用实例

    工作内容：
    - 配置 CORS
    - 注册 API 路由
    - 托管前端静态资源
    - SPA 路由兜底
    """
    app = FastAPI(
        title="西窗",
        description="多模态智能助手 - 支持文本、语音、图片、视频",
        version="1.0.0",
    )

    # CORS 配置
    # allow_origins=["*"] 时浏览器规范不允许 credentials=True，前端 fetch 默认也不带 cookie
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        logger.info(f"--> {request.method} {request.url.path}")
        try:
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000
            logger.info(f"<-- {request.method} {request.url.path} {response.status_code} ({duration:.2f}ms)")
            return response
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"<-- {request.method} {request.url.path} ERROR: {e} ({duration:.2f}ms)")
            raise

    # 注册 API 路由
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(milvus.router, prefix="/api/milvus", tags=["milvus"])
    app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])

    # 打印所有注册的路由（调试用）
    for route in app.routes:
        if hasattr(route, 'path'):
            methods = ",".join(sorted(getattr(route, "methods", []) or []))
            logger.info("Registered route: {} [{}]", route.path, methods)

    # 挂载静态资源目录（用于访问上传的文件）
    project_root = Path(__file__).resolve().parents[3]
    statics_dir = project_root / "server" / "statics"
    if statics_dir.exists():
        app.mount("/statics", StaticFiles(directory=str(statics_dir)), name="statics")

    # Vue3 前端托管
    dist_dir = project_root / "web" / "dist"
    assets_dir = dist_dir / "assets"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        """返回前端首页"""
        index_path = dist_dir / "index.html"
        if index_path.exists():
            with index_path.open("r", encoding="utf-8") as f:
                return HTMLResponse(f.read())
        dev_index = project_root / "web" / "index.html"
        if dev_index.exists():
            with dev_index.open("r", encoding="utf-8") as f:
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
        # API 路径返回 JSON 格式的 404
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                {"detail": f"API endpoint /{full_path} not found"},
                status_code=404
            )

        # 非 API 路径返回 SPA 页面
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        index_path = dist_dir / "index.html"
        if index_path.exists():
            with index_path.open("r", encoding="utf-8") as f:
                return HTMLResponse(f.read())

        return HTMLResponse("<h1>Page not found</h1>", status_code=404)

    logger.info("Application started with DEBUG={}", settings.DEBUG)
    return app


app = create_app()
