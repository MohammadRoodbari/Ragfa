# RAGfa UI

React + Vite frontend for the RAGfa document intelligence API.

## Stack

- **React 18** — UI components
- **Vite** — dev server with built-in API proxy
- **Tabler Icons** — icon font (CDN)
- **Space Grotesk / Inter / JetBrains Mono** — Google Fonts

No UI library dependencies — all styling is vanilla CSS-in-JS with design tokens.

---

## Quick start

```bash
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/health`, `/ingest`, and `/query` to `http://localhost:8000` by default.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `""` (uses Vite proxy) | Base URL of the FastAPI backend |

Copy `.env.example` to `.env.local` and set `VITE_API_URL` if your API runs on a different host or you're deploying the frontend separately.

```bash
cp .env.example .env.local
# edit VITE_API_URL=https://api.your-domain.com
```

---

## Project structure

```
src/
  lib/
    api.js          # All fetch calls — one function per endpoint
  hooks/
    useHealth.js    # GET /health — liveness check
    useIngest.js    # POST /ingest/file|text + polling GET /ingest/jobs/{id}
    useChat.js      # POST /query + POST /query/stream (SSE)
  components/
    TopBar.jsx      # Logo + health indicator dropdown
    Sidebar.jsx     # Upload zone, text modal, document list with status
    ChatArea.jsx    # Message list, welcome screen, suggested prompts
    InputBar.jsx    # Textarea, send button, stream toggle, session badge
  App.jsx           # Root layout wiring all pieces together
  index.css         # Design tokens (CSS vars) + global reset + animations
  main.jsx          # ReactDOM entry point
index.html          # HTML shell with font/icon CDN links
vite.config.js      # Vite config + dev proxy rules
```

---

## API endpoints used

| Method | Path | Hook |
|---|---|---|
| `GET` | `/health` | `useHealth` |
| `POST` | `/ingest/file` | `useIngest.addFile` |
| `POST` | `/ingest/text` | `useIngest.addText` |
| `GET` | `/ingest/jobs/{task_id}` | `useIngest` (polling every 1.5 s) |
| `POST` | `/query` | `useChat` (blocking mode) |
| `POST` | `/query/stream` | `useChat` (streaming SSE mode) |

---

## Build for production

```bash
npm run build      # outputs to dist/
npm run preview    # serve the built output locally
```
