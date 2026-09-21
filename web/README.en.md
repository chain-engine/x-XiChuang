English | [中文](README.md)

# XiChuang Web

The frontend application for the XiChuang project, built with **Vue 3 + Vite**, providing the user interface for the multimodal AI assistant.

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Vue | 3.4+ | Reactive UI framework |
| Vite | 5.0+ | Build tool & dev server |
| Marked | 12.0+ | Markdown rendering |
| highlight.js | 11.10+ | Code syntax highlighting |
| DOMPurify | 3.2+ | HTML sanitization (XSS prevention) |

## Quick Start

### Prerequisites

- **Node.js** >= 18.0
- **npm** >= 9.0 (or pnpm / yarn)

### Install Dependencies

```bash
npm install
```

### Development Mode

```bash
npm run dev
```

Visit http://localhost:5173 after startup. API requests are automatically proxied to the backend at `http://localhost:8000`.

> **Note**: The backend service must be running in development mode. See [server/README.md](../server/README.md) for details.

### Build for Production

```bash
npm run build
```

Output is placed in the `dist/` directory and can be served directly by the backend (static file mounting is already configured in FastAPI).

### Preview Build Output

```bash
npm run preview
```

## Project Structure

```
web/
├── index.html                # HTML entry point
├── package.json              # Dependencies & scripts
├── vite.config.js            # Vite config (proxy, alias, build)
├── public/                   # Static assets (not processed by build)
└── src/
    ├── main.js               # Application entry
    ├── App.vue               # Root component
    ├── components/           # UI components
    │   ├── ChatPanel.vue     # Main chat panel
    │   ├── InputArea.vue     # Message input area
    │   ├── MessageItem.vue   # Single message display
    │   ├── MessageList.vue   # Message list
    │   └── Sidebar.vue       # Sidebar
    ├── composables/          # Composable functions
    │   ├── useChat.js        # Chat logic
    │   └── useRecorder.js    # Recording logic
    ├── services/             # API services
    │   └── api.js            # Backend API client
    ├── assets/               # Static assets (processed by build)
    │   └── images/
    └── styles/               # Global styles
        └── variables.css     # CSS variable definitions
```

## Dev Proxy Configuration

In development mode, Vite proxies `/api` requests to the backend:

```
Browser → http://localhost:5173/api/* → http://localhost:8000/api/*
```

To change the proxy target, edit the `server.proxy` section in `vite.config.js`.
