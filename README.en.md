[中文](README.md) | English

# XiChuang (西窗)

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

## Project Introduction

**XiChuang (西窗)** is a multimodal intelligent assistant built with LangChain + LangGraph + FastAPI. The name is inspired by a famous line from the Tang Dynasty poet Li Shangyin: "When shall we trim the candle by the western window, and talk about the night rain in the mountains of Ba."

The project supports text, voice, image, audio, and video inputs, with built-in integration of mainstream LLMs including Qwen, DeepSeek, GLM, Doubao, and Kimi. It leverages LangGraph state graph orchestration to implement Retrieval-Augmented Generation (RAG) and intelligent conversation. It serves as a production-grade development framework for multimodal AI assistants, suitable for use cases such as intelligent customer service, knowledge Q&A, and content creation.

---

## Quick Start

XiChuang adopts a frontend-backend separated architecture. The server and web applications maintain independent development environments and deployment workflows. Please refer to the corresponding sub-project documentation:

| Sub-project | Description | Documentation |
|-------------|-------------|---------------|
| **Server** | FastAPI backend service providing AI conversation, session management, and knowledge retrieval | [server/README.md](server/README.md) |
| **Web** | Vue 3 frontend application providing the user interface | [web/README.md](web/README.md) |

> **Docker One-Click Deployment**: The project root provides a `docker-compose.yml` that can simultaneously start MySQL, Milvus, and the application service. See the server documentation for details.

---

## Project Structure

```
x-XiChuang/
│
├── server/                              # Backend Service (FastAPI)
│   ├── src/                             # Source Code Directory
│   │   ├── main.py                      # FastAPI Application Entry
│   │   ├── core/                        # Core Layer: Config, Logger, Exceptions, Middleware
│   │   ├── constants/                   # Constants Layer: Business Enums, Status Codes
│   │   ├── schemas/                     # Schema Layer: Pydantic Data Models
│   │   ├── repositories/                # Data Access Layer: Database Repository Abstractions
│   │   ├── services/                    # Business Logic Layer: Chat, Conversation, Milvus Services
│   │   ├── api/                         # API Router Layer: RESTful Endpoint Definitions
│   │   │   └── v1/                      # v1 Versioned Routes
│   │   │       ├── health.py            # Health Check Endpoints
│   │   │       ├── conversations.py     # Conversation & Chat Endpoints
│   │   │       └── milvus.py            # Milvus Management Endpoints
│   │   ├── agent/                       # AI Agent Layer: Model Router, Multimodal, Memory, Knowledge
│   │   ├── infras/                      # Infrastructure Layer: Database, Milvus, File Storage
│   │   ├── models/                      # ORM Models Layer
│   │   └── utils/                       # Utilities Layer: Common Utility Functions
│   ├── tests/                           # Unit Tests
│   ├── scripts/                         # Scripts Directory
│   ├── docs/                            # Server Documentation
│   ├── examples/                        # Example Code
│   ├── logs/                            # Runtime Logs
│   ├── pyproject.toml                   # Python Project Configuration & Dependencies
│   └── README.md                        # Server Documentation
│
├── web/                                 # Frontend Application (Vue 3)
│   ├── src/                             # Source Code Directory
│   │   ├── main.js                      # Vue Application Entry
│   │   ├── App.vue                      # Root Component
│   │   ├── components/                  # UI Components: Sidebar, ChatPanel, MessageList, etc.
│   │   ├── composables/                 # Composables: Chat Logic, Recording Logic
│   │   ├── services/                    # API Service Layer
│   │   └── styles/                      # Style Files
│   ├── index.html                       # HTML Entry
│   ├── package.json                     # Frontend Dependencies
│   ├── vite.config.js                   # Vite Build Configuration
│   └── README.md                        # Web Documentation
│
├── docker-compose.yml                   # Docker Compose Orchestration File
├── Dockerfile                           # Multi-stage Build Dockerfile
├── LICENSE                              # MIT Open Source License
├── README.md                            # Project Chinese Documentation
└── README.en.md                         # Project English Documentation
```

---

## Tech Stack

### Frontend

| Category | Technology | Version | Description |
|----------|------------|---------|-------------|
| Framework | Vue | 3.4+ | Progressive JavaScript framework |
| Build Tool | Vite | 5.0+ | Next-generation frontend build tool |
| Markdown Rendering | marked | 12.0+ | Markdown parsing and rendering |
| Code Highlighting | highlight.js | 11.10+ | Code syntax highlighting |
| Security Filtering | DOMPurify | 3.2+ | XSS prevention |

### Backend

| Category | Technology | Version | Description |
|----------|------------|---------|-------------|
| Language | Python | 3.11+ | Core development language |
| Web Framework | FastAPI | 0.111+ | Async web framework |
| ASGI Server | Uvicorn | 0.29+ | Production-grade ASGI server |
| LLM Orchestration | LangChain | 0.3+ | LLM application development framework |
| Flow Orchestration | LangGraph | 0.1+ | Conversation flow state graph orchestration |
| Data Validation | Pydantic | v2 | Request/response data models |
| ORM | SQLAlchemy | 2.0+ | Database object-relational mapping |
| Vector Database | pymilvus | 2.3+ | Milvus Python client |
| Speech Recognition | OpenAI Whisper | - | Speech-to-text (ASR) |
| Audio Processing | pydub | 0.25+ | Audio format conversion |
| Logging | loguru | 0.7+ | Structured logging framework |
| HTTP Client | httpx | 0.27+ | Async HTTP client |
| Object Storage | oss2 | 2.18+ | Aliyun OSS client |

### Data Storage

| Category | Technology | Version | Description |
|----------|------------|---------|-------------|
| Relational Database | MySQL | 8.0+ | Session and message persistence |
| Vector Database | Milvus | 2.4+ | Knowledge base vector retrieval (RAG) |
| Object Storage | Aliyun OSS / Local Filesystem | - | Multimedia file storage |

### AI Models

| Category | Provider | Model Example | Usage |
|----------|----------|---------------|-------|
| Text Chat | Qwen | qwen-plus-latest | General conversation (default) |
| Multimodal | Qwen | qwen-vl-plus | Image/audio/video understanding |
| Text Chat | DeepSeek | deepseek-chat | General conversation |
| Text Chat | Zhipu GLM | glm-4 | General conversation |
| Text Chat | Doubao | doubao-pro | General conversation |
| Text Chat | Moonshot | moonshot-v1-8k | General conversation |
| Speech-to-Text | OpenAI | whisper-1 | Speech recognition |
| Text Embedding | Qwen | text-embedding-v1 | Knowledge base embedding |

### DevOps

| Category | Technology | Description |
|----------|------------|-------------|
| Containerization | Docker | Application containerized deployment |
| Orchestration | Docker Compose | Multi-service orchestration (MySQL + Milvus + App) |
| Dependency Management | uv | Python package management and virtual environment |
| Code Quality | Ruff | Code formatting and static analysis |
| Type Checking | mypy | Static type checking |
| Testing Framework | pytest | Unit testing and code coverage |

---

## API Documentation

XiChuang is built on FastAPI and provides complete OpenAPI specification documentation:

| Document Type | Access URL | Description |
|---------------|------------|-------------|
| Swagger UI | `http://localhost:8000/docs` | Interactive API documentation with online debugging |
| ReDoc | `http://localhost:8000/redoc` | Read-only API documentation for reference |
| OpenAPI JSON | `http://localhost:8000/openapi.json` | OpenAPI 3.x specification file |

### Core API Endpoints

#### Conversation Management (/api/v1/conversations)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/conversations/` | Get conversation list |
| `POST` | `/api/v1/conversations/` | Create new conversation |
| `GET` | `/api/v1/conversations/providers` | Get available model provider list |
| `GET` | `/api/v1/conversations/{id}` | Get conversation details (with messages) |
| `POST` | `/api/v1/conversations/{id}/update` | Update conversation |
| `POST` | `/api/v1/conversations/{id}/delete` | Delete conversation |
| `POST` | `/api/v1/conversations/{id}/messages` | Save messages |
| `POST` | `/api/v1/conversations/message` | Send message (non-streaming) |
| `POST` | `/api/v1/conversations/stream` | Send message (SSE streaming) |
| `POST` | `/api/v1/conversations/upload` | Upload file for conversation |

#### Milvus Management (/api/v1/milvus)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/milvus/stats` | Get Milvus statistics |
| `GET` | `/api/v1/milvus/collections` | List all collections |
| `POST` | `/api/v1/milvus/search` | Vector search |
| `GET` | `/api/v1/milvus/knowledge-status` | Knowledge base status diagnostics |
| `POST` | `/api/v1/milvus/rebuild-knowledge` | Rebuild knowledge base vectors |

#### Health Check (/api/v1/health)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health/live` | Liveness check |
| `GET` | `/api/v1/health/ready` | Readiness check |

> **Access Control**: The current version uses an open access mode without authentication. For production environments, it is recommended to add an authentication layer through a reverse proxy (such as Nginx) or API gateway.

---

## Storage Configuration

XiChuang supports two file storage modes, switchable via the `STORAGE_TYPE` environment variable:

### Local File Storage (Default)

Suitable for development environments and small-scale deployments. Files are stored on the server's local disk.

```bash
STORAGE_TYPE=local
```

- Storage path: `server/statics/` directory organized by type (images, audio, videos, files)
- Access method: Direct access via FastAPI static file service

### Aliyun OSS Object Storage

Suitable for production environments, providing high-availability and high-concurrency file storage capabilities.

```bash
STORAGE_TYPE=oss
ALIYUN_OSS_ACCESS_KEY_ID=your-access-key-id
ALIYUN_OSS_ACCESS_KEY_SECRET=your-access-key-secret
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_BUCKET_NAME=your-bucket-name
```

### Database Storage

| Storage Type | Technology | Purpose | Configuration |
|--------------|------------|---------|---------------|
| Relational Data | MySQL 8.0+ | Sessions, messages, user data | `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` |
| Vector Data | Milvus 2.4+ | Knowledge base embedding vectors | `MILVUS_HOST`, `MILVUS_PORT` |

> **Notes**:
> - Both MySQL and Milvus can be deployed with one click via Docker Compose without manual installation
> - For production, it is recommended to enable master-slave replication for MySQL and cluster mode for Milvus
> - The knowledge base index only includes the root `README.md` and `.md` files under the `data/knowledge/` directory. Web chat history is not automatically indexed

---

## License

This project is released under the [MIT License](LICENSE).

Copyright (c) 2026 John Young

---

## References

| Technology | Official Documentation |
|------------|----------------------|
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
| Aliyun OSS | https://help.aliyun.com/product/31815.html |

---

## Contact

- **Author**: John Young (夜雨诗来)
- **Email**: john.young@foxmail.com
- **Gitee**: https://gitee.com/yeyushilai
- **GitHub**: https://github.com/yeyushilai
- **Project**: https://github.com/chain-engine/x-XiChuang
