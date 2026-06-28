# -*- coding: utf-8 -*-
"""
FastAPI 应用入口

用于 uvicorn 启动服务。
"""

import sys
from pathlib import Path

# 将 server 目录添加到 Python 路径
server_dir = Path(__file__).parent.parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from src.app.main import app
