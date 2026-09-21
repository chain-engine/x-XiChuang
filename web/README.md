[English](README.en.md) | 中文

# 西窗 Web 端

西窗项目的前端应用，基于 **Vue 3 + Vite** 构建，为多模态智能交互助手提供用户界面。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 响应式 UI 框架 |
| Vite | 5.0+ | 构建工具与开发服务器 |
| Marked | 12.0+ | Markdown 渲染 |
| highlight.js | 11.10+ | 代码高亮 |
| DOMPurify | 3.2+ | HTML 净化（防 XSS） |

## 快速开始

### 环境要求

- **Node.js** >= 18.0
- **npm** >= 9.0（或 pnpm / yarn）

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

启动后访问 http://localhost:5173，API 请求会自动代理到后端 `http://localhost:8000`。

> **前提条件**：开发模式下需要后端服务已启动，详见 [server/README.md](../server/README.md)。

### 构建生产版本

```bash
npm run build
```

产物输出到 `dist/` 目录，可由后端服务直接托管（已在 FastAPI 中配置静态文件挂载）。

### 预览构建产物

```bash
npm run preview
```

## 项目结构

```
web/
├── index.html                # HTML 入口
├── package.json              # 依赖与脚本配置
├── vite.config.js            # Vite 配置（代理、别名、构建）
├── public/                   # 静态资源（不经过构建处理）
└── src/
    ├── main.js               # 应用入口
    ├── App.vue               # 根组件
    ├── components/           # UI 组件
    │   ├── ChatPanel.vue     # 聊天主面板
    │   ├── InputArea.vue     # 消息输入区域
    │   ├── MessageItem.vue   # 单条消息展示
    │   ├── MessageList.vue   # 消息列表
    │   └── Sidebar.vue       # 侧边栏
    ├── composables/          # 组合式函数
    │   ├── useChat.js        # 聊天逻辑
    │   └── useRecorder.js    # 录音逻辑
    ├── services/             # API 服务
    │   └── api.js            # 后端接口封装
    ├── assets/               # 静态资源（经构建处理）
    │   └── images/
    └── styles/               # 全局样式
        └── variables.css     # CSS 变量定义
```

## 开发代理配置

开发模式下，Vite 会将 `/api` 前缀的请求代理到后端服务：

```
浏览器 → http://localhost:5173/api/* → http://localhost:8000/api/*
```

如需修改代理目标，编辑 `vite.config.js` 中的 `server.proxy` 配置。
