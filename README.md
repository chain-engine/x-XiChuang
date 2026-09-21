[English](README.en.md) | 中文

# 西窗（XiChuang）

<p>
<img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
<img src="https://img.shields.io/badge/Vue-3.4-4fc08d?logo=vue.js&logoColor=white" alt="Vue" />
<img src="https://img.shields.io/badge/LangChain-🦜-orange" alt="LangChain" />
<img src="https://img.shields.io/badge/LangGraph-1c3c3c?logo=langchain&logoColor=white" alt="LangGraph" />
<img src="https://img.shields.io/badge/Milvus-00a1ea?logo=milvus&logoColor=white" alt="Milvus" />
<img src="https://img.shields.io/badge/Whisper-7b3ff4?logo=openai&logoColor=white" alt="Whisper" />
</p>

---

## 项目简介

**西窗（XiChuang）** 是一款基于 LangChain + LangGraph + FastAPI 构建的多模态智能交互助手，取自李商隐名句「何当共剪西窗烛，却话巴山夜雨时」。

项目支持文本、语音、图片、音频、视频等多种模态输入，内置千问、DeepSeek、GLM、豆包、Kimi 等主流大语言模型，通过 LangGraph 状态图编排实现检索增强生成（RAG）与智能对话。适合作为多模态 AI 助手的生产级开发框架，可用于智能客服、知识问答、内容创作等业务场景。

---

## 快速开始

西窗采用前后端分离架构，服务端与 Web 端各自维护独立的开发环境和部署流程。请根据您的需求参考对应的子项目文档：

| 子项目 | 说明 | 文档链接 |
|--------|------|----------|
| **服务端（Server）** | FastAPI 后端服务，提供 AI 对话、会话管理、知识库检索等核心能力 | [server/README.md](server/README.md) |
| **Web 端（Web）** | Vue 3 前端应用，提供用户交互界面 | [web/README.md](web/README.md) |

> **Docker 一键部署**：项目根目录提供 `docker-compose.yml`，可同时启动 MySQL、Milvus 及应用服务，详见服务端文档。

---

## 项目结构

```
x-XiChuang/
│
├── server/                              # 后端服务（FastAPI）
│   ├── src/                             # 源代码目录
│   │   ├── main.py                      # FastAPI 应用入口
│   │   ├── core/                        # 核心层：配置管理、日志、异常、中间件
│   │   ├── constants/                   # 常量层：业务枚举、状态码定义
│   │   ├── schemas/                     # Schema 层：Pydantic 数据模型
│   │   ├── repositories/                # 数据访问层：数据库仓储抽象
│   │   ├── services/                    # 业务逻辑层：对话、会话、Milvus 服务
│   │   ├── api/                         # API 路由层：RESTful 接口定义
│   │   │   └── v1/                      # v1 版本路由
│   │   │       ├── health.py            # 健康检查接口
│   │   │       ├── conversations.py     # 会话与对话接口
│   │   │       └── milvus.py            # Milvus 管理接口
│   │   ├── agent/                       # AI 智能体层：模型路由、多模态、记忆、知识库
│   │   ├── infras/                      # 基础设施层：数据库、Milvus、文件存储
│   │   ├── models/                      # ORM 模型层
│   │   └── utils/                       # 工具层：通用工具函数
│   ├── tests/                           # 单元测试
│   ├── scripts/                         # 脚本目录
│   ├── docs/                            # 服务端文档
│   ├── examples/                        # 示例代码
│   ├── logs/                            # 运行日志
│   ├── pyproject.toml                   # Python 项目配置与依赖声明
│   └── README.md                        # 服务端文档
│
├── web/                                 # 前端应用（Vue 3）
│   ├── src/                             # 源代码目录
│   │   ├── main.js                      # Vue 应用入口
│   │   ├── App.vue                      # 根组件
│   │   ├── components/                  # UI 组件：侧边栏、聊天面板、消息列表等
│   │   ├── composables/                 # 组合式函数：聊天逻辑、录音逻辑
│   │   ├── services/                    # API 服务层
│   │   └── styles/                      # 样式文件
│   ├── index.html                       # HTML 入口
│   ├── package.json                     # 前端依赖声明
│   ├── vite.config.js                   # Vite 构建配置
│   └── README.md                        # Web 端文档
│
├── docker-compose.yml                   # Docker Compose 编排文件
├── Dockerfile                           # 多阶段构建 Dockerfile
├── LICENSE                              # MIT 开源协议
├── README.md                            # 项目中文文档
└── README.en.md                         # 项目英文文档
```

---

## 技术栈

### 前端技术栈

| 分类 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 框架 | Vue | 3.4+ | 渐进式 JavaScript 框架 |
| 构建工具 | Vite | 5.0+ | 下一代前端构建工具 |
| Markdown 渲染 | marked | 12.0+ | Markdown 解析与渲染 |
| 代码高亮 | highlight.js | 11.10+ | 代码语法高亮 |
| 安全过滤 | DOMPurify | 3.2+ | XSS 防护 |

### 后端技术栈

| 分类 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 开发语言 | Python | 3.11+ | 核心开发语言 |
| Web 框架 | FastAPI | 0.111+ | 异步 Web 框架 |
| ASGI 服务器 | Uvicorn | 0.29+ | 生产级 ASGI 服务器 |
| LLM 编排 | LangChain | 0.3+ | LLM 应用开发框架 |
| 流程编排 | LangGraph | 0.1+ | 对话流程状态图编排 |
| 数据验证 | Pydantic | v2 | 请求/响应数据模型 |
| ORM | SQLAlchemy | 2.0+ | 数据库对象关系映射 |
| 向量数据库 | pymilvus | 2.3+ | Milvus Python 客户端 |
| 语音识别 | OpenAI Whisper | - | 语音转文字（ASR） |
| 音频处理 | pydub | 0.25+ | 音频格式转换 |
| 日志 | loguru | 0.7+ | 结构化日志框架 |
| HTTP 客户端 | httpx | 0.27+ | 异步 HTTP 客户端 |
| 对象存储 | oss2 | 2.18+ | 阿里云 OSS 客户端 |

### 数据存储

| 分类 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 关系型数据库 | MySQL | 8.0+ | 会话与消息持久化存储 |
| 向量数据库 | Milvus | 2.4+ | 知识库向量检索（RAG） |
| 对象存储 | 阿里云 OSS / 本地文件系统 | - | 多媒体文件存储 |

### AI 模型

| 分类 | 提供商 | 模型示例 | 用途 |
|------|--------|----------|------|
| 文本对话 | 通义千问 | qwen-plus-latest | 通用对话（默认） |
| 多模态理解 | 通义千问 | qwen-vl-plus | 图片/音频/视频理解 |
| 文本对话 | DeepSeek | deepseek-chat | 通用对话 |
| 文本对话 | 智谱 GLM | glm-4 | 通用对话 |
| 文本对话 | 火山豆包 | doubao-pro | 通用对话 |
| 文本对话 | Moonshot | moonshot-v1-8k | 通用对话 |
| 语音转文字 | OpenAI | whisper-1 | 语音识别 |
| 文本向量化 | 通义千问 | text-embedding-v1 | 知识库 Embedding |

### 部署运维

| 分类 | 技术 | 说明 |
|------|------|------|
| 容器化 | Docker | 应用容器化部署 |
| 编排 | Docker Compose | 多服务编排（MySQL + Milvus + App） |
| 依赖管理 | uv | Python 包管理与虚拟环境 |
| 代码质量 | Ruff | 代码格式化与静态检查 |
| 类型检查 | mypy | 静态类型检查 |
| 测试框架 | pytest | 单元测试与覆盖率 |

---

## API 文档说明

西窗基于 FastAPI 构建，提供完整的 OpenAPI 规范文档：

| 文档类型 | 访问地址 | 说明 |
|----------|----------|------|
| Swagger UI | `http://localhost:8000/docs` | 交互式 API 文档，支持在线调试 |
| ReDoc | `http://localhost:8000/redoc` | 只读 API 文档，适合查阅 |
| OpenAPI JSON | `http://localhost:8000/openapi.json` | OpenAPI 3.x 规范文件 |

### 核心 API 接口清单

#### 会话管理（/api/v1/conversations）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/conversations/` | 获取会话列表 |
| `POST` | `/api/v1/conversations/` | 创建新会话 |
| `GET` | `/api/v1/conversations/providers` | 获取可用模型提供商列表 |
| `GET` | `/api/v1/conversations/{id}` | 获取会话详情（含消息） |
| `POST` | `/api/v1/conversations/{id}/update` | 更新会话 |
| `POST` | `/api/v1/conversations/{id}/delete` | 删除会话 |
| `POST` | `/api/v1/conversations/{id}/messages` | 保存消息 |
| `POST` | `/api/v1/conversations/message` | 发送消息（非流式） |
| `POST` | `/api/v1/conversations/stream` | 发送消息（SSE 流式） |
| `POST` | `/api/v1/conversations/upload` | 上传文件对话 |

#### Milvus 管理（/api/v1/milvus）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/milvus/stats` | 获取 Milvus 统计信息 |
| `GET` | `/api/v1/milvus/collections` | 列出所有 Collection |
| `POST` | `/api/v1/milvus/search` | 向量检索 |
| `GET` | `/api/v1/milvus/knowledge-status` | 知识库状态诊断 |
| `POST` | `/api/v1/milvus/rebuild-knowledge` | 重建知识库向量 |

#### 健康检查（/api/v1/health）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health/live` | 存活检查 |
| `GET` | `/api/v1/health/ready` | 就绪检查 |

> **权限控制**：当前版本 API 为开放访问模式，未启用认证机制。生产环境建议通过反向代理（如 Nginx）或 API 网关添加认证层。

---

## 存储配置说明

西窗支持两种文件存储模式，通过环境变量 `STORAGE_TYPE` 切换：

### 本地文件存储（默认）

适用于开发环境和小规模部署，文件存储在服务器本地磁盘。

```bash
STORAGE_TYPE=local
```

- 存储路径：`server/statics/` 目录下按类型分类（images、audio、videos、files）
- 访问方式：通过 FastAPI 静态文件服务直接访问

### 阿里云 OSS 对象存储

适用于生产环境，提供高可用、高并发的文件存储能力。

```bash
STORAGE_TYPE=oss
ALIYUN_OSS_ACCESS_KEY_ID=your-access-key-id
ALIYUN_OSS_ACCESS_KEY_SECRET=your-access-key-secret
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_BUCKET_NAME=your-bucket-name
```

### 数据库存储

| 存储类型 | 技术 | 用途 | 配置项 |
|----------|------|------|--------|
| 关系型数据 | MySQL 8.0+ | 会话、消息、用户数据 | `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE` |
| 向量数据 | Milvus 2.4+ | 知识库 Embedding 向量 | `MILVUS_HOST`、`MILVUS_PORT` |

> **注意事项**：
> - MySQL 和 Milvus 均可通过 Docker Compose 一键部署，无需手动安装
> - 生产环境建议对 MySQL 启用主从复制，对 Milvus 启用集群模式
> - 知识库索引仅包含根目录 `README.md` 和 `data/knowledge/` 目录下的 `.md` 文件，Web 聊天记录不会自动索引

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源协议发布。

Copyright (c) 2026 John Young

---

## 参考资料

| 技术 | 官方文档 |
|------|----------|
| Python | https://docs.python.org/3/ |
| FastAPI | https://fastapi.tiangolo.com/ |
| Vue.js | https://vuejs.org/ |
| Vite | https://vitejs.dev/ |
| LangChain | https://python.langchain.com/ |
| LangGraph | https://langchain-ai.github.io/langgraph/ |
| Milvus | https://milvus.io/docs |
| SQLAlchemy | https://docs.sqlalchemy.org/ |
| Pydantic | https://docs.pydantic.dev/ |
| uv | https://docs.astral.sh/uv/ |
| Docker | https://docs.docker.com/ |
| Docker Compose | https://docs.docker.com/compose/ |
| loguru | https://loguru.readthedocs.io/ |
| Ruff | https://docs.astral.sh/ruff/ |
| pytest | https://docs.pytest.org/ |
| OpenAI Whisper | https://platform.openai.com/docs/guides/speech-to-text |
| 阿里云 OSS | https://help.aliyun.com/product/31815.html |

---

## 联系方式

- **作者**：John Young（夜雨诗来）
- **邮箱**：john.young@foxmail.com
- **Gitee**：https://gitee.com/yeyushilai
- **GitHub**：https://github.com/yeyushilai
- **项目地址**：https://github.com/chain-engine/x-XiChuang
